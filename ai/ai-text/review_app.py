from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import os
from pathlib import Path
from typing import Any

import streamlit as st

from src.review_store import (
    ReviewStore,
    create_review_state,
    discover_draft_files,
    discover_review_conditions,
    discover_result_groups,
    read_json_or_jsonl,
    summarize_draft,
)


APP_ROOT = Path(__file__).resolve().parent
DATASET_DIR = APP_ROOT / "dataset" / "tester" / "정우현"
WORKSPACE_ID = "WS-001"
OWNER = "정우현"
REVIEW_ROOT = Path(
    os.environ.get("WOOJUIN_REVIEW_ROOT", APP_ROOT / "review-data")
).resolve()


def configured_result_roots() -> list[Path]:
    roots = [
        APP_ROOT / "results",
        APP_ROOT / "review-inputs" / WORKSPACE_ID,
        APP_ROOT / "results" / "자동 카테고리 테스트",
    ]
    extra = os.environ.get("WOOJUIN_DRAFT_ROOTS", "")
    roots.extend(Path(value.strip()) for value in extra.split(os.pathsep) if value.strip())
    unique: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        resolved = root.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def choose_result_folder(initial_dir: Path) -> Path | None:
    """로컬 실행 환경에서 Windows 폴더 선택 창을 엽니다."""
    import tkinter as tk
    from tkinter import filedialog

    dialog = tk.Tk()
    dialog.withdraw()
    dialog.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(
            title="AI 테스트 결과 폴더 선택",
            initialdir=str(initial_dir if initial_dir.is_dir() else APP_ROOT),
            mustexist=True,
        )
    finally:
        dialog.destroy()
    return Path(selected).resolve() if selected else None


def display_path(path: Path) -> str:
    try:
        return path.relative_to(APP_ROOT).as_posix()
    except ValueError:
        return str(path)


def make_review_key(group: Path, condition: Path, draft_file: Path) -> str:
    try:
        stable_path = draft_file.resolve().relative_to(APP_ROOT).as_posix()
    except ValueError:
        stable_path = f"{group.name}/{condition.name}/{draft_file.name}"
    digest = hashlib.sha1(stable_path.encode("utf-8")).hexdigest()[:8]
    return f"{group.name}-{condition.name}-{digest}"


def category_names(state: dict[str, Any]) -> dict[str, str]:
    return {
        category["categoryId"]: category["name"]
        for category in state["categories"]
    }


def rows_to_csv(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


st.set_page_config(
    page_title="AI 카테고리 결과 검토",
    page_icon="🪐",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    """
    <style>
      .block-container {padding-top: 1.3rem; padding-bottom: 4rem; max-width: 1450px;}
      [data-testid="stMetricValue"] {font-size: 1.45rem;}
      .review-card {
        border: 1px solid rgba(128,128,128,.25);
        border-radius: 16px;
        padding: 1.15rem 1.25rem;
        background: rgba(128,128,128,.035);
        margin: .6rem 0 1rem;
      }
      .initial-category {
        display: inline-block; border-radius: 999px; padding: .3rem .75rem;
        background: rgba(91,110,225,.15); font-weight: 700;
      }
      .stButton button {border-radius: 10px;}
      div[data-testid="stNotification"] {border-radius: 12px;}
    </style>
    """,
    unsafe_allow_html=True,
)


st.title("AI 카테고리 결과 검토")
st.caption(
    "실험 결과 폴더를 선택하고, 각 데이터의 초기 카테고리를 승인하거나 직접 수정합니다."
)

st.subheader("결과 폴더 선택")
folder_path_col, folder_button_col = st.columns([5, 1])
manual_folder = folder_path_col.text_input(
    "결과 폴더 경로",
    value=st.session_state.get("selected-result-folder", ""),
    placeholder=str(APP_ROOT / "results"),
    help="테스트 결과 폴더 또는 여러 결과 폴더가 들어 있는 상위 폴더를 선택하세요.",
)
if folder_button_col.button("폴더 선택", use_container_width=True):
    try:
        initial_folder = Path(manual_folder) if manual_folder.strip() else APP_ROOT / "results"
        selected_folder = choose_result_folder(initial_folder)
        if selected_folder is not None:
            st.session_state["selected-result-folder"] = str(selected_folder)
            st.rerun()
    except Exception as exc:
        st.error(f"폴더 선택 창을 열 수 없습니다: {exc}")

roots = configured_result_roots()
if manual_folder.strip():
    chosen_root = Path(manual_folder.strip()).expanduser().resolve()
    if chosen_root.is_dir():
        roots.insert(0, chosen_root)
    else:
        st.warning("입력한 결과 폴더가 존재하지 않습니다.")
groups = discover_result_groups(roots)
preferred_root_text = manual_folder.strip() or next(
    (
        value.strip()
        for value in os.environ.get("WOOJUIN_DRAFT_ROOTS", "").split(os.pathsep)
        if value.strip()
    ),
    "",
)
if preferred_root_text:
    preferred_root = Path(preferred_root_text).expanduser().resolve()
    groups = sorted(
        groups,
        key=lambda path: (not path.is_relative_to(preferred_root), str(path).casefold()),
    )
if not groups:
    st.warning("검토할 결과 폴더를 찾지 못했습니다.")
    st.write("아래 위치에 `상위 실행 폴더/실험 조건/review-draft.json` 구조로 저장하세요.")
    for root in roots:
        st.code(str(root))
    st.stop()

selection_col, condition_col, file_col = st.columns([1.4, 1.4, 1])
group = selection_col.selectbox(
    "상위 결과 폴더",
    groups,
    format_func=display_path,
)
conditions = discover_review_conditions(group)
condition = condition_col.selectbox(
    "실험 조건",
    conditions,
    format_func=lambda path: (
        "기본 결과" if path == group else path.relative_to(group).as_posix()
    ),
)
draft_files = discover_draft_files(condition)
draft_file = file_col.selectbox(
    "결과 JSON",
    draft_files,
    format_func=lambda path: path.name,
)

try:
    draft_payload = read_json_or_jsonl(draft_file)
    draft_summary = summarize_draft(draft_payload, DATASET_DIR)
except (ValueError, OSError, json.JSONDecodeError) as exc:
    st.error(f"결과 파일을 읽을 수 없습니다: {exc}")
    st.stop()

review_key = make_review_key(group, condition, draft_file)
store = ReviewStore(REVIEW_ROOT, WORKSPACE_ID, review_key=review_key)

summary_columns = st.columns(4)
summary_columns[0].metric(
    "결과 매칭",
    f"{draft_summary['matchedItemCount']}/{draft_summary['draftRowCount']}",
)
summary_columns[1].metric("초안 데이터", draft_summary["draftRowCount"])
summary_columns[2].metric("초기 카테고리", draft_summary["categoryCount"])
summary_columns[3].metric(
    "이번 검토 제외",
    draft_summary["unmatchedDatasetItemCount"],
    help="전체 원본 데이터 중 이번 결과 JSON에 포함되지 않은 데이터입니다.",
)

if not draft_summary["matchedDraftReady"]:
    st.error(
        "결과 JSON의 모든 데이터가 원본 데이터와 연결되고 초기 카테고리가 있어야 합니다. "
        f"초안 초과 {draft_summary['unmatchedDraftRowCount']}개, "
        "카테고리 없는 항목 "
        f"{draft_summary['matchedItemCount'] - draft_summary['rowsWithCategory']}개"
    )
    st.stop()

if not store.exists:
    st.info(
        f"선택한 조건: `{condition.name}` · "
        f"초기 카테고리 {draft_summary['categoryCount']}개"
    )
    with st.expander("초기 카테고리 보기"):
        st.write(", ".join(draft_summary["categoryNames"]))
    if st.button("이 결과 검토 시작", type="primary", key="start-review"):
        state = create_review_state(
            workspace_id=WORKSPACE_ID,
            owner=OWNER,
            dataset_dir=DATASET_DIR,
            mode="ai_review",
            draft_payload=draft_payload,
            auto_approve_categories=True,
            matched_drafts_only=True,
        )
        state["experiment"] = {
            "group": str(group),
            "condition": str(condition),
            "draftFile": str(draft_file),
        }
        store.initialize(state, draft_payload=draft_payload)
        st.rerun()
    st.stop()

state = store.load()
completed, total = store.progress(state)
pending_items = [
    item
    for item in state["items"]
    if item["decision"] in {"PENDING", "UNCERTAIN"}
]

st.sidebar.subheader("검토 진행")
st.sidebar.write(f"**{group.name}**")
st.sidebar.caption(condition.name)
st.sidebar.progress(completed / total if total else 0)
st.sidebar.write(f"{completed} / {total}")
page = st.sidebar.radio("화면", ["데이터 검토", "결과표"])

if page == "데이터 검토":
    if not pending_items:
        st.success("모든 데이터 검토가 끝났습니다. 왼쪽에서 ‘결과표’를 확인하세요.")
        if st.button("결과표 보기", type="primary"):
            st.session_state["show-results"] = True
        st.stop()

    selected_id = st.selectbox(
        f"검토할 데이터 · 남은 {len(pending_items)}개",
        [item["itemId"] for item in pending_items],
        format_func=lambda item_id: next(
            f"{item['localId']} · {item['title'][:80]}"
            for item in pending_items
            if item["itemId"] == item_id
        ),
    )
    item = next(value for value in state["items"] if value["itemId"] == selected_id)
    st.markdown(
        f"""
        <div class="review-card">
          <div class="initial-category">{html.escape(item.get('aiCategoryName') or '카테고리 없음')}</div>
          <h2>{html.escape(item['title'])}</h2>
          <p>{html.escape(item.get('aiSummary') or 'AI가 생성한 요약이 없습니다.')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    action_col, reject_col = st.columns([1, 1.25], gap="large")
    with action_col:
        st.subheader("초기 카테고리가 맞나요?")
        st.write(f"**초기 카테고리:** {item.get('aiCategoryName') or '없음'}")
        if st.button(
            "승인하고 다음으로",
            type="primary",
            use_container_width=True,
            key=f"approve-{item['itemId']}",
        ):
            store.simple_review_item(state, item["itemId"], approved=True)
            st.rerun()
        with st.expander("원본 데이터 보기"):
            st.text_area(
                "원문",
                value=item["content"],
                height=280,
                disabled=True,
                label_visibility="collapsed",
            )
            st.caption(item["sourcePath"])
    with reject_col:
        st.subheader("틀렸다면 직접 수정")
        existing_names = sorted(category_names(state).values())
        st.caption("기존 이름을 그대로 입력하거나 새로운 카테고리명을 적을 수 있습니다.")
        with st.form(f"reject-{item['itemId']}", clear_on_submit=True):
            corrected = st.text_input(
                "올바른 카테고리 이름",
                placeholder="예: 백엔드 개발",
            )
            note = st.text_input(
                "메모",
                placeholder="선택 사항",
            )
            rejected = st.form_submit_button(
                "거부하고 이 이름으로 변경",
                use_container_width=True,
            )
        if existing_names:
            st.caption("현재 카테고리: " + " · ".join(existing_names))
        if rejected:
            try:
                store.simple_review_item(
                    state,
                    item["itemId"],
                    approved=False,
                    corrected_category=corrected,
                    note=note,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.rerun()

else:
    category_rows, item_rows = store.simple_report(state)
    if completed == total:
        st.success(f"전체 {total}개 데이터 검토가 완료되었습니다.")
    else:
        st.info(f"현재 {completed}/{total}개가 검토되었습니다. 표는 자동 갱신됩니다.")

    st.subheader("1. 카테고리별 검토 결과")
    st.caption("승인율과 거부율은 현재까지 검토한 데이터 기준입니다.")
    st.dataframe(
        category_rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "승인율": st.column_config.ProgressColumn(
                "승인율", min_value=0, max_value=100, format="%.1f%%"
            ),
            "거부율": st.column_config.ProgressColumn(
                "거부율", min_value=0, max_value=100, format="%.1f%%"
            ),
        },
    )
    st.download_button(
        "카테고리 결과 CSV 받기",
        data=rows_to_csv(category_rows),
        file_name=f"{condition.name}-category-summary.csv",
        mime="text/csv",
    )

    st.subheader("2. 데이터별 검토 결과")
    st.dataframe(item_rows, use_container_width=True, hide_index=True)
    download_col, json_col = st.columns(2)
    download_col.download_button(
        "데이터 상세 CSV 받기",
        data=rows_to_csv(item_rows),
        file_name=f"{condition.name}-item-details.csv",
        mime="text/csv",
        use_container_width=True,
    )
    json_col.download_button(
        "전체 결과 JSON 받기",
        data=json.dumps(
            {
                "experiment": state.get("experiment", {}),
                "progress": {"reviewed": completed, "total": total},
                "categorySummary": category_rows,
                "itemDetails": item_rows,
            },
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
        file_name=f"{condition.name}-review-results.json",
        mime="application/json",
        use_container_width=True,
    )
