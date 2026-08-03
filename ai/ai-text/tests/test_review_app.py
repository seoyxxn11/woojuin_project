import json
from pathlib import Path

from streamlit.testing.v1 import AppTest


def make_full_draft(app_root: Path, root: Path) -> Path:
    dataset = app_root / "dataset" / "tester" / "정우현"
    condition = root / "run-001" / "existing-11-plus-ai"
    condition.mkdir(parents=True)
    rows = [
        {
            "sourcePath": path.relative_to(dataset).as_posix(),
            "title": f"검토 제목 {path.stem}",
            "generatedSummary": f"{path.parent.name} 데이터 요약",
            "generatedCategory": path.parent.name,
        }
        for path in sorted(dataset.glob("*/*.txt"))
    ]
    (condition / "review-draft.json").write_text(
        json.dumps({"items": rows}, ensure_ascii=False),
        encoding="utf-8",
    )
    return condition


def test_simple_review_flow_discovers_condition_and_starts(
    monkeypatch, tmp_path: Path
):
    app_root = Path(__file__).resolve().parents[1]
    condition = make_full_draft(app_root, tmp_path / "drafts")
    monkeypatch.setenv("WOOJUIN_DRAFT_ROOTS", str(tmp_path / "drafts"))
    monkeypatch.setenv("WOOJUIN_REVIEW_ROOT", str(tmp_path / "review-data"))
    app = AppTest.from_file(
        str(app_root / "review_app.py"), default_timeout=20
    ).run()

    assert app.title[0].value == "AI 카테고리 결과 검토"
    assert any(selectbox.label == "상위 결과 폴더" for selectbox in app.selectbox)
    assert any(selectbox.label == "실험 조건" for selectbox in app.selectbox)
    assert any(selectbox.label == "결과 JSON" for selectbox in app.selectbox)
    assert any(metric.value == "112/112" for metric in app.metric)
    assert any(metric.value == "11" for metric in app.metric)
    assert app.button(key="start-review").disabled is False

    app.button(key="start-review").click()
    app.run()

    assert any(
        selectbox.label.startswith("검토할 데이터")
        for selectbox in app.selectbox
    )
    approve_button = next(
        button for button in app.button if button.label == "승인하고 다음으로"
    )
    assert any("initial-category" in block.value for block in app.markdown)
    assert any(condition.name in caption.value for caption in app.sidebar.caption)

    approve_button.click()
    app.run()
    app.radio[0].set_value("결과표")
    app.run()

    assert any(
        subheader.value == "1. 카테고리별 검토 결과"
        for subheader in app.subheader
    )
    assert any(
        subheader.value == "2. 데이터별 검토 결과"
        for subheader in app.subheader
    )
    assert len(app.dataframe) == 2


def test_simple_report_records_approval_and_rejection(tmp_path: Path):
    from src.review_store import ReviewStore, create_review_state

    dataset = tmp_path / "dataset" / "테스터"
    (dataset / "기존A").mkdir(parents=True)
    (dataset / "기존B").mkdir(parents=True)
    (dataset / "기존A" / "0001-memo.txt").write_text("첫 데이터", encoding="utf-8")
    (dataset / "기존B" / "0002-memo.txt").write_text("둘째 데이터", encoding="utf-8")
    draft = {
        "items": [
            {
                "sourcePath": "기존A/0001-memo.txt",
                "title": "첫 제목",
                "summary": "첫 요약",
                "category": "AI 카테고리",
            },
            {
                "sourcePath": "기존B/0002-memo.txt",
                "title": "둘째 제목",
                "summary": "둘째 요약",
                "category": "AI 카테고리",
            },
        ]
    }
    state = create_review_state(
        "WS-001",
        "테스터",
        dataset,
        "ai_review",
        draft_payload=draft,
        auto_approve_categories=True,
    )
    store = ReviewStore(tmp_path / "reviews", "WS-001", "condition-a")
    store.initialize(state, draft)
    first, second = state["items"]

    store.simple_review_item(state, first["itemId"], approved=True)
    store.simple_review_item(
        state,
        second["itemId"],
        approved=False,
        corrected_category="사람 수정 카테고리",
    )
    category_rows, item_rows = store.simple_report(state)

    assert category_rows == [
        {
            "초기 카테고리": "AI 카테고리",
            "초기 데이터 수": 2,
            "승인": 1,
            "거부": 1,
            "검토 완료": 2,
            "승인율": 50.0,
            "거부율": 50.0,
        }
    ]
    assert item_rows[0]["검토 결과"] == "승인"
    assert item_rows[0]["요약"] == "첫 요약"
    assert item_rows[1]["검토 결과"] == "거부"
    assert item_rows[1]["거부 후 카테고리"] == "사람 수정 카테고리"
