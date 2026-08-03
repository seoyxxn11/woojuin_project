from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
DECISIONS = {
    "PENDING",
    "APPROVE",
    "REJECT",
    "MOVE",
    "NEW",
    "EXCLUDE",
    "UNCERTAIN",
}
WORKSPACE_NAME_PATTERN = re.compile(r"[^0-9A-Za-z가-힣._-]+")


@dataclass(frozen=True)
class WorkspacePreset:
    workspace_id: str
    owner: str
    dataset_dir: Path
    default_mode: str


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def safe_workspace_key(value: str) -> str:
    normalized = WORKSPACE_NAME_PATTERN.sub("-", value.strip()).strip("-")
    if not normalized:
        raise ValueError("워크스페이스 ID가 비어 있습니다.")
    return normalized


def category_id(name: str, existing_ids: Iterable[str] = ()) -> str:
    base = hashlib.sha1(name.strip().encode("utf-8")).hexdigest()[:8].upper()
    candidate = f"CAT-{base}"
    used = set(existing_ids)
    suffix = 2
    while candidate in used:
        candidate = f"CAT-{base}-{suffix}"
        suffix += 1
    return candidate


def read_json_or_jsonl(path: Path) -> Any:
    raw = path.read_text(encoding="utf-8-sig").strip()
    if not raw:
        raise ValueError(f"AI 초안 파일이 비어 있습니다: {path}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        rows = []
        for line_number, line in enumerate(raw.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"AI 초안 {line_number}번째 줄이 올바른 JSON이 아닙니다."
                ) from exc
        return rows


def discover_draft_folders(roots: Iterable[Path]) -> list[Path]:
    """허용된 결과 루트 아래에서 JSON/JSONL이 들어 있는 폴더를 찾습니다."""
    folders: set[Path] = set()
    for root in roots:
        resolved = root.resolve()
        if not resolved.is_dir():
            continue
        for pattern in ("*.json", "*.jsonl"):
            for path in resolved.rglob(pattern):
                if path.is_file() and path.stat().st_size > 0:
                    folders.add(path.parent.resolve())
    return sorted(folders, key=lambda path: str(path).casefold(), reverse=True)


def discover_result_groups(roots: Iterable[Path]) -> list[Path]:
    """결과 루트 바로 아래에서 검토 JSON을 포함한 상위 실행 폴더를 찾습니다."""
    groups: set[Path] = set()
    for root in roots:
        resolved = root.resolve()
        if not resolved.is_dir():
            continue
        if discover_draft_files(resolved):
            groups.add(resolved)
        for child in resolved.iterdir():
            if child.is_dir() and discover_draft_folders([child]):
                groups.add(child.resolve())
    return sorted(groups, key=lambda path: str(path).casefold(), reverse=True)


def discover_draft_files(folder: Path) -> list[Path]:
    """선택한 폴더 바로 아래의 비어 있지 않은 JSON/JSONL 파일을 반환합니다."""
    if not folder.is_dir():
        return []
    files = [
        path.resolve()
        for path in folder.iterdir()
        if path.is_file()
        and path.suffix.lower() in {".json", ".jsonl"}
        and path.stat().st_size > 0
    ]
    return sorted(
        files,
        key=lambda path: (
            {
                "review-draft.json": 0,
                "review-draft.jsonl": 0,
                "evaluation-results.json": 1,
            }.get(path.name, 2),
            path.name.casefold(),
        ),
    )


def _dataset_item(path: Path, dataset_dir: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8-sig").strip()
    relative = path.relative_to(dataset_dir).as_posix()
    legacy_category = path.parent.name
    title = path.stem
    display_content = raw
    existing_summary = ""
    input_type = "memo"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        input_type = str(parsed.get("type") or "unknown").lower()
        title = str(parsed.get("title") or parsed.get("url") or path.stem).strip()
        existing_summary = str(parsed.get("summary") or "").strip()
        display_content = str(
            parsed.get("content")
            or parsed.get("summary")
            or parsed.get("preview", {}).get("description")
            or raw
        ).strip()
    match = re.match(r"^(?P<id>\d+)", path.stem)
    local_id = match.group("id") if match else path.stem
    item_id = f"{dataset_dir.name}-{local_id}"
    return {
        "itemId": item_id,
        "localId": local_id,
        "title": title,
        "content": display_content,
        "rawInput": raw,
        "inputType": input_type,
        "sourcePath": relative,
        "legacyCategory": legacy_category,
        "aiCategoryId": None,
        "aiCategoryName": None,
        "aiSummary": existing_summary,
        "aiReason": "",
        "finalCategoryId": None,
        "decision": "PENDING",
        "reviewNote": "",
        "reviewedAt": None,
    }


def load_folder_dataset(dataset_dir: Path) -> list[dict[str, Any]]:
    if not dataset_dir.is_dir():
        raise ValueError(f"데이터셋 폴더가 없습니다: {dataset_dir}")
    paths = sorted(
        (path for path in dataset_dir.glob("*/*.txt") if path.is_file()),
        key=lambda value: value.relative_to(dataset_dir).as_posix().casefold(),
    )
    if not paths:
        raise ValueError(f"검토할 TXT 데이터가 없습니다: {dataset_dir}")
    items = [_dataset_item(path, dataset_dir) for path in paths]
    duplicated = _duplicates(item["itemId"] for item in items)
    if duplicated:
        raise ValueError(f"중복된 항목 ID가 있습니다: {sorted(duplicated)}")
    return items


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicated: set[str] = set()
    for value in values:
        if value in seen:
            duplicated.add(value)
        seen.add(value)
    return duplicated


def _lookup_draft_row(
    draft_rows: list[dict[str, Any]], item: dict[str, Any]
) -> dict[str, Any] | None:
    candidates = {
        item["itemId"],
        item["localId"],
        item["sourcePath"],
        Path(item["sourcePath"]).name,
        Path(item["sourcePath"]).stem,
    }
    for row in draft_rows:
        row_ids = {
            str(row.get(key, ""))
            for key in ("itemId", "testId", "id", "localId", "sourcePath")
        }
        if candidates & row_ids:
            return row
    return None


def _draft_category(row: dict[str, Any]) -> tuple[str | None, str, str]:
    parsed = row.get("parsedResponse")
    if not isinstance(parsed, dict):
        parsed = {}
    category_value = (
        row.get("aiCategory")
        or row.get("generatedCategory")
        or row.get("category")
        or parsed.get("category")
    )
    reason = str(
        row.get("aiReason")
        or row.get("reason")
        or row.get("categoryReason")
        or parsed.get("reason")
        or ""
    ).strip()
    if isinstance(category_value, dict):
        name = str(category_value.get("name") or "").strip()
        identifier = str(category_value.get("id") or "").strip() or None
        return identifier, name, reason
    return None, str(category_value or "").strip(), reason


def _draft_summary(row: dict[str, Any]) -> str:
    parsed = row.get("parsedResponse")
    if not isinstance(parsed, dict):
        parsed = {}
    return str(
        row.get("summary")
        or row.get("generatedSummary")
        or row.get("aiSummary")
        or parsed.get("summary")
        or ""
    ).strip()


def normalize_draft(payload: Any) -> tuple[list[dict[str, Any]], dict[str, str]]:
    descriptions: dict[str, str] = {}
    if isinstance(payload, dict):
        raw_categories = payload.get("categories", [])
        rows = payload.get("items") or payload.get("predictions") or payload.get("results")
        if rows is None:
            rows = [payload]
    elif isinstance(payload, list):
        raw_categories = []
        rows = payload
    else:
        raise ValueError("AI 초안은 JSON 객체, 배열 또는 JSONL이어야 합니다.")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("AI 초안의 items/predictions/results는 객체 배열이어야 합니다.")
    if isinstance(raw_categories, list):
        for category in raw_categories:
            if isinstance(category, dict) and category.get("name"):
                descriptions[str(category["name"]).strip()] = str(
                    category.get("description") or ""
                ).strip()
    return list(rows), descriptions


def summarize_draft(payload: Any, dataset_dir: Path) -> dict[str, Any]:
    """검토 시작 전에 초안과 현재 데이터셋의 매칭 상태를 요약합니다."""
    rows, descriptions = normalize_draft(payload)
    items = load_folder_dataset(dataset_dir)
    matched_item_ids: set[str] = set()
    generated_categories: set[str] = set(descriptions)
    rows_with_category = 0
    for item in items:
        row = _lookup_draft_row(rows, item)
        if row is None:
            continue
        matched_item_ids.add(item["itemId"])
        _, name, _ = _draft_category(row)
        if name:
            rows_with_category += 1
            generated_categories.add(name)
    return {
        "datasetItemCount": len(items),
        "draftRowCount": len(rows),
        "matchedItemCount": len(matched_item_ids),
        "unmatchedDatasetItemCount": len(items) - len(matched_item_ids),
        "unmatchedDraftRowCount": max(0, len(rows) - len(matched_item_ids)),
        "rowsWithCategory": rows_with_category,
        "categoryCount": len(generated_categories),
        "categoryNames": sorted(generated_categories),
        "ready": (
            len(matched_item_ids) == len(items)
            and rows_with_category == len(items)
        ),
        "matchedDraftReady": (
            bool(matched_item_ids)
            and len(rows) == len(matched_item_ids)
            and rows_with_category == len(matched_item_ids)
        ),
    }


def create_review_state(
    workspace_id: str,
    owner: str,
    dataset_dir: Path,
    mode: str,
    draft_payload: Any | None = None,
    use_legacy_as_draft: bool = False,
    auto_approve_categories: bool = False,
    matched_drafts_only: bool = False,
) -> dict[str, Any]:
    if mode not in {"ai_review", "blind"}:
        raise ValueError("검토 모드는 ai_review 또는 blind여야 합니다.")
    items = load_folder_dataset(dataset_dir)
    draft_rows: list[dict[str, Any]] = []
    descriptions: dict[str, str] = {}
    if draft_payload is not None:
        draft_rows, descriptions = normalize_draft(draft_payload)
    if matched_drafts_only and draft_rows:
        items = [
            item for item in items
            if _lookup_draft_row(draft_rows, item) is not None
        ]

    category_names: list[str] = []
    item_drafts: dict[str, tuple[str | None, str, str]] = {}
    for item in items:
        if mode == "blind":
            continue
        row = _lookup_draft_row(draft_rows, item) if draft_rows else None
        if row is not None:
            draft = _draft_category(row)
        elif use_legacy_as_draft:
            draft = (None, item["legacyCategory"], "기존 정답 라벨로 초기화")
        else:
            draft = (None, "", "")
        item_drafts[item["itemId"]] = draft
        if draft[1] and draft[1] not in category_names:
            category_names.append(draft[1])

    category_ids: dict[str, str] = {}
    categories = []
    used_ids: set[str] = set()
    for name in category_names:
        requested_ids = {
            draft[0]
            for draft in item_drafts.values()
            if draft[1] == name and draft[0]
        }
        identifier = next(iter(requested_ids), None) or category_id(name, used_ids)
        if identifier in used_ids:
            identifier = category_id(name, used_ids)
        used_ids.add(identifier)
        category_ids[name] = identifier
        categories.append(
            {
                "categoryId": identifier,
                "name": name,
                "description": descriptions.get(name, ""),
                "status": "APPROVED" if auto_approve_categories else "PENDING",
                "source": "LEGACY_PREVIEW" if use_legacy_as_draft else "AI",
                "createdAt": now_iso(),
                "updatedAt": now_iso(),
            }
        )

    for item in items:
        draft = item_drafts.get(item["itemId"])
        if draft and draft[1]:
            item["aiCategoryId"] = category_ids[draft[1]]
            item["aiCategoryName"] = draft[1]
            item["aiReason"] = draft[2]
            item["finalCategoryId"] = category_ids[draft[1]]
            row = _lookup_draft_row(draft_rows, item) if draft_rows else None
            if row is not None:
                item["aiSummary"] = _draft_summary(row) or item["aiSummary"]
                item["title"] = str(row.get("title") or item["title"]).strip()

    timestamp = now_iso()
    return {
        "schemaVersion": SCHEMA_VERSION,
        "workspaceId": safe_workspace_key(workspace_id),
        "owner": owner.strip(),
        "mode": mode,
        "datasetDir": str(dataset_dir.resolve()),
        "createdAt": timestamp,
        "updatedAt": timestamp,
        "goldVersions": [],
        "categories": categories,
        "items": items,
    }


class ReviewStore:
    def __init__(
        self, root: Path, workspace_id: str, review_key: str | None = None
    ):
        self.workspace_id = safe_workspace_key(workspace_id)
        self.review_key = safe_workspace_key(review_key) if review_key else None
        self.workspace_dir = root / self.workspace_id
        if self.review_key:
            self.workspace_dir = self.workspace_dir / "reviews" / self.review_key
        self.state_path = self.workspace_dir / "review-state.json"
        self.history_path = self.workspace_dir / "review-history.jsonl"
        self.draft_path = self.workspace_dir / "ai-draft.json"
        self.gold_root = self.workspace_dir / "gold"

    @property
    def exists(self) -> bool:
        return self.state_path.is_file()

    def initialize(
        self,
        state: dict[str, Any],
        draft_payload: Any | None,
        overwrite: bool = False,
    ) -> None:
        if self.exists and not overwrite:
            raise FileExistsError("이미 검토 상태가 있습니다.")
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        if draft_payload is not None:
            self._write_json(self.draft_path, draft_payload)
        self.save(state)
        self._append_history(
            {
                "action": "INITIALIZE",
                "mode": state["mode"],
                "itemCount": len(state["items"]),
                "categoryCount": len(state["categories"]),
            }
        )

    def load(self) -> dict[str, Any]:
        if not self.exists:
            raise FileNotFoundError("검토 상태가 아직 생성되지 않았습니다.")
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def save(self, state: dict[str, Any]) -> None:
        state["updatedAt"] = now_iso()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(self.state_path, state)

    def add_category(
        self, state: dict[str, Any], name: str, description: str = ""
    ) -> str:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("카테고리 이름을 입력하세요.")
        if any(
            category["name"].casefold() == clean_name.casefold()
            for category in state["categories"]
        ):
            raise ValueError("같은 이름의 카테고리가 이미 있습니다.")
        identifier = category_id(
            clean_name, (category["categoryId"] for category in state["categories"])
        )
        state["categories"].append(
            {
                "categoryId": identifier,
                "name": clean_name,
                "description": description.strip(),
                "status": "APPROVED",
                "source": "HUMAN",
                "createdAt": now_iso(),
                "updatedAt": now_iso(),
            }
        )
        self._record_and_save(
            state,
            {"action": "CATEGORY_CREATE", "categoryId": identifier, "after": clean_name},
        )
        return identifier

    def update_category(
        self,
        state: dict[str, Any],
        identifier: str,
        name: str,
        description: str,
        status: str,
    ) -> None:
        category = self._category(state, identifier)
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("카테고리 이름을 입력하세요.")
        if status not in {"PENDING", "APPROVED", "UNCERTAIN"}:
            raise ValueError("올바르지 않은 카테고리 상태입니다.")
        if any(
            other["categoryId"] != identifier
            and other["name"].casefold() == clean_name.casefold()
            for other in state["categories"]
        ):
            raise ValueError("같은 이름의 카테고리가 이미 있습니다.")
        before = deepcopy(category)
        category.update(
            {
                "name": clean_name,
                "description": description.strip(),
                "status": status,
                "updatedAt": now_iso(),
            }
        )
        for item in state["items"]:
            if item.get("aiCategoryId") == identifier:
                item["aiCategoryName"] = clean_name
        self._record_and_save(
            state,
            {
                "action": "CATEGORY_UPDATE",
                "categoryId": identifier,
                "before": before,
                "after": deepcopy(category),
            },
        )

    def merge_category(
        self, state: dict[str, Any], source_id: str, target_id: str
    ) -> None:
        if source_id == target_id:
            raise ValueError("서로 다른 카테고리를 선택하세요.")
        source = self._category(state, source_id)
        target = self._category(state, target_id)
        moved = 0
        for item in state["items"]:
            if item.get("finalCategoryId") == source_id:
                item["finalCategoryId"] = target_id
                if item["decision"] in {"PENDING", "APPROVE"}:
                    item["decision"] = "MOVE"
                item["reviewedAt"] = now_iso()
                moved += 1
        state["categories"] = [
            category
            for category in state["categories"]
            if category["categoryId"] != source_id
        ]
        self._record_and_save(
            state,
            {
                "action": "CATEGORY_MERGE",
                "source": {"categoryId": source_id, "name": source["name"]},
                "target": {"categoryId": target_id, "name": target["name"]},
                "movedItemCount": moved,
            },
        )

    def delete_empty_category(self, state: dict[str, Any], identifier: str) -> None:
        category = self._category(state, identifier)
        if any(item.get("finalCategoryId") == identifier for item in state["items"]):
            raise ValueError("콘텐츠가 남아 있는 카테고리는 삭제할 수 없습니다.")
        state["categories"] = [
            value
            for value in state["categories"]
            if value["categoryId"] != identifier
        ]
        self._record_and_save(
            state,
            {
                "action": "CATEGORY_DELETE",
                "categoryId": identifier,
                "before": category,
            },
        )

    def review_item(
        self,
        state: dict[str, Any],
        item_id: str,
        decision: str,
        final_category_id: str | None,
        note: str = "",
    ) -> None:
        if decision not in DECISIONS - {"PENDING"}:
            raise ValueError("올바르지 않은 검토 결과입니다.")
        item = self._item(state, item_id)
        if decision != "EXCLUDE":
            if not final_category_id:
                raise ValueError("최종 카테고리를 선택하세요.")
            self._category(state, final_category_id)
        before = {
            "decision": item["decision"],
            "finalCategoryId": item.get("finalCategoryId"),
            "reviewNote": item.get("reviewNote", ""),
        }
        item.update(
            {
                "decision": decision,
                "finalCategoryId": None if decision == "EXCLUDE" else final_category_id,
                "reviewNote": note.strip(),
                "reviewedAt": now_iso(),
            }
        )
        self._record_and_save(
            state,
            {
                "action": "ITEM_REVIEW",
                "itemId": item_id,
                "before": before,
                "after": {
                    "decision": item["decision"],
                    "finalCategoryId": item.get("finalCategoryId"),
                    "reviewNote": item["reviewNote"],
                },
            },
        )

    def simple_review_item(
        self,
        state: dict[str, Any],
        item_id: str,
        approved: bool,
        corrected_category: str = "",
        note: str = "",
    ) -> None:
        item = self._item(state, item_id)
        if approved:
            if not item.get("aiCategoryId"):
                raise ValueError("초기 카테고리가 없어 승인할 수 없습니다.")
            self.review_item(
                state,
                item_id,
                "APPROVE",
                item["aiCategoryId"],
                note,
            )
            return
        clean_name = corrected_category.strip()
        if not clean_name:
            raise ValueError("거부할 때는 올바른 카테고리 이름을 입력하세요.")
        existing = next(
            (
                category
                for category in state["categories"]
                if category["name"].casefold() == clean_name.casefold()
            ),
            None,
        )
        if existing is None:
            identifier = self.add_category(state, clean_name)
        else:
            identifier = existing["categoryId"]
        self.review_item(state, item_id, "REJECT", identifier, note)

    @staticmethod
    def simple_report(
        state: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        category_rows: list[dict[str, Any]] = []
        initial_names = sorted(
            {
                item.get("aiCategoryName") or "카테고리 없음"
                for item in state["items"]
            }
        )
        for name in initial_names:
            items = [
                item
                for item in state["items"]
                if (item.get("aiCategoryName") or "카테고리 없음") == name
            ]
            approved = sum(item["decision"] == "APPROVE" for item in items)
            rejected = sum(item["decision"] == "REJECT" for item in items)
            reviewed = approved + rejected
            category_rows.append(
                {
                    "초기 카테고리": name,
                    "초기 데이터 수": len(items),
                    "승인": approved,
                    "거부": rejected,
                    "검토 완료": reviewed,
                    "승인율": round(approved / reviewed * 100, 1)
                    if reviewed
                    else 0.0,
                    "거부율": round(rejected / reviewed * 100, 1)
                    if reviewed
                    else 0.0,
                }
            )
        names = {
            category["categoryId"]: category["name"]
            for category in state["categories"]
        }
        item_rows = []
        for item in state["items"]:
            if item["decision"] == "APPROVE":
                result = "승인"
            elif item["decision"] == "REJECT":
                result = "거부"
            else:
                result = "미검토"
            item_rows.append(
                {
                    "데이터 ID": item["itemId"],
                    "제목": item["title"],
                    "요약": item.get("aiSummary") or "",
                    "초기 카테고리": item.get("aiCategoryName") or "",
                    "검토 결과": result,
                    "거부 후 카테고리": (
                        names.get(item.get("finalCategoryId"), "")
                        if item["decision"] == "REJECT"
                        else ""
                    ),
                    "최종 카테고리": (
                        names.get(item.get("finalCategoryId"), "")
                        if result != "미검토"
                        else ""
                    ),
                    "검토 메모": item.get("reviewNote", ""),
                }
            )
        return category_rows, item_rows

    def validate_for_gold(self, state: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        pending = [
            item["itemId"]
            for item in state["items"]
            if item["decision"] in {"PENDING", "UNCERTAIN"}
        ]
        if pending:
            errors.append(f"미검토 또는 보류 콘텐츠가 {len(pending)}개 있습니다.")
        uncertain_categories = [
            category["name"]
            for category in state["categories"]
            if category["status"] != "APPROVED"
        ]
        if uncertain_categories:
            errors.append(
                f"승인되지 않은 카테고리가 {len(uncertain_categories)}개 있습니다."
            )
        active_items = [
            item for item in state["items"] if item["decision"] != "EXCLUDE"
        ]
        missing = [
            item["itemId"]
            for item in active_items
            if not item.get("finalCategoryId")
        ]
        if missing:
            errors.append(f"최종 카테고리가 없는 콘텐츠가 {len(missing)}개 있습니다.")
        active_category_ids = {
            item.get("finalCategoryId") for item in active_items if item.get("finalCategoryId")
        }
        empty_categories = [
            category["name"]
            for category in state["categories"]
            if category["categoryId"] not in active_category_ids
        ]
        if empty_categories:
            errors.append(f"빈 카테고리가 {len(empty_categories)}개 있습니다.")
        names = [category["name"].casefold() for category in state["categories"]]
        if len(names) != len(set(names)):
            errors.append("중복된 카테고리 이름이 있습니다.")
        return errors

    def finalize_gold(
        self, state: dict[str, Any], reviewer: str, change_note: str = ""
    ) -> Path:
        errors = self.validate_for_gold(state)
        if errors:
            raise ValueError("\n".join(errors))
        next_version = len(state.get("goldVersions", [])) + 1
        version = f"v{next_version}"
        version_dir = self.gold_root / version
        if version_dir.exists():
            raise FileExistsError(f"이미 {version} GOLD가 있습니다.")
        version_dir.mkdir(parents=True)
        category_counts = self.category_counts(state)
        categories = [
            {
                "categoryId": category["categoryId"],
                "name": category["name"],
                "description": category["description"],
                "itemCount": category_counts.get(category["categoryId"], 0),
            }
            for category in state["categories"]
        ]
        items = [
            {
                "itemId": item["itemId"],
                "sourcePath": item["sourcePath"],
                "title": item["title"],
                "legacyCategory": item["legacyCategory"],
                "goldCategoryId": item.get("finalCategoryId"),
                "decision": item["decision"],
                "excluded": item["decision"] == "EXCLUDE",
                "reviewNote": item["reviewNote"],
            }
            for item in state["items"]
        ]
        approved = sum(item["decision"] == "APPROVE" for item in state["items"])
        summary = {
            "workspaceId": state["workspaceId"],
            "owner": state["owner"],
            "goldVersion": version,
            "mode": state["mode"],
            "reviewer": reviewer.strip(),
            "changeNote": change_note.strip(),
            "confirmedAt": now_iso(),
            "totalItems": len(items),
            "includedItems": sum(not item["excluded"] for item in items),
            "excludedItems": sum(item["excluded"] for item in items),
            "categoryCount": len(categories),
            "approvedWithoutMove": approved,
            "modifiedItems": sum(
                item["decision"] in {"REJECT", "MOVE", "NEW"}
                for item in state["items"]
            ),
        }
        self._write_json(version_dir / "categories.json", categories)
        self._write_json(version_dir / "items.json", items)
        self._write_json(version_dir / "summary.json", summary)
        state.setdefault("goldVersions", []).append(
            {"version": version, "path": str(version_dir), "confirmedAt": now_iso()}
        )
        self._record_and_save(
            state,
            {
                "action": "GOLD_FINALIZE",
                "version": version,
                "reviewer": reviewer.strip(),
                "changeNote": change_note.strip(),
            },
        )
        return version_dir

    @staticmethod
    def category_counts(state: dict[str, Any]) -> dict[str, int]:
        counts = {category["categoryId"]: 0 for category in state["categories"]}
        for item in state["items"]:
            identifier = item.get("finalCategoryId")
            if item["decision"] != "EXCLUDE" and identifier in counts:
                counts[identifier] += 1
        return counts

    @staticmethod
    def progress(state: dict[str, Any]) -> tuple[int, int]:
        return (
            sum(
                item["decision"] not in {"PENDING", "UNCERTAIN"}
                for item in state["items"]
            ),
            len(state["items"]),
        )

    def _record_and_save(
        self, state: dict[str, Any], history: dict[str, Any]
    ) -> None:
        self.save(state)
        self._append_history(history)

    def _append_history(self, event: dict[str, Any]) -> None:
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "workspaceId": self.workspace_id,
            "occurredAt": now_iso(),
            **event,
        }
        with self.history_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    @staticmethod
    def _category(state: dict[str, Any], identifier: str) -> dict[str, Any]:
        for category in state["categories"]:
            if category["categoryId"] == identifier:
                return category
        raise ValueError(f"카테고리를 찾을 수 없습니다: {identifier}")

    @staticmethod
    def _item(state: dict[str, Any], item_id: str) -> dict[str, Any]:
        for item in state["items"]:
            if item["itemId"] == item_id:
                return item
        raise ValueError(f"콘텐츠를 찾을 수 없습니다: {item_id}")
