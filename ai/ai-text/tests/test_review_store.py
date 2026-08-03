import json
from pathlib import Path

import pytest

from src.review_store import (
    ReviewStore,
    create_review_state,
    discover_draft_files,
    discover_draft_folders,
    discover_review_conditions,
    read_json_or_jsonl,
    summarize_draft,
)


def make_dataset(root: Path) -> Path:
    dataset = root / "tester" / "테스터"
    first = dataset / "학습·지식"
    second = dataset / "음식·맛집"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    (first / "0001-url.txt").write_text(
        json.dumps(
            {
                "type": "URL",
                "title": "Spring Boot 학습",
                "url": "https://example.com/spring",
                "summary": "Spring Boot 서버 개발을 학습한다.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (second / "0002-memo.txt").write_text("서울의 파스타 맛집을 기록한다.", encoding="utf-8")
    return dataset


def test_ai_draft_is_normalized_and_matched_by_source_path(tmp_path: Path):
    dataset = make_dataset(tmp_path)
    draft = {
        "categories": [
            {"name": "백엔드 개발", "description": "서버 개발 자료"},
            {"name": "맛집", "description": "음식점 정보"},
        ],
        "items": [
            {
                "sourcePath": "학습·지식/0001-url.txt",
                "aiCategory": "백엔드 개발",
                "aiReason": "Spring 콘텐츠",
            },
            {
                "sourcePath": "음식·맛집/0002-memo.txt",
                "aiCategory": "맛집",
            },
        ],
    }

    state = create_review_state("WS-001", "테스터", dataset, "ai_review", draft)

    assert len(state["items"]) == 2
    assert {category["name"] for category in state["categories"]} == {
        "백엔드 개발",
        "맛집",
    }
    first = next(item for item in state["items"] if item["localId"] == "0001")
    assert first["aiCategoryName"] == "백엔드 개발"
    assert first["aiReason"] == "Spring 콘텐츠"
    assert first["finalCategoryId"] == first["aiCategoryId"]


def test_blind_mode_does_not_expose_ai_assignment(tmp_path: Path):
    dataset = make_dataset(tmp_path)

    state = create_review_state(
        "WS-002",
        "테스터",
        dataset,
        "blind",
        draft_payload=[
            {"sourcePath": "학습·지식/0001-url.txt", "category": "백엔드 개발"}
        ],
    )

    assert state["categories"] == []
    assert all(item["aiCategoryName"] is None for item in state["items"])
    assert all(item["finalCategoryId"] is None for item in state["items"])


def test_review_history_and_gold_are_written_separately(tmp_path: Path):
    dataset = make_dataset(tmp_path)
    state = create_review_state(
        "WS-001",
        "테스터",
        dataset,
        "ai_review",
        use_legacy_as_draft=True,
    )
    store = ReviewStore(tmp_path / "review-data", "WS-001")
    store.initialize(state, draft_payload={"items": []})

    for category in list(state["categories"]):
        store.update_category(
            state,
            category["categoryId"],
            category["name"],
            f"{category['name']} 설명",
            "APPROVED",
        )
    for item in list(state["items"]):
        store.review_item(
            state,
            item["itemId"],
            "APPROVE",
            item["finalCategoryId"],
            "확인 완료",
        )

    destination = store.finalize_gold(state, "reviewer-01", "최초 확정")

    assert store.draft_path.is_file()
    assert store.history_path.is_file()
    assert (destination / "categories.json").is_file()
    assert (destination / "items.json").is_file()
    summary = json.loads((destination / "summary.json").read_text(encoding="utf-8"))
    assert summary["goldVersion"] == "v1"
    assert summary["totalItems"] == 2
    assert summary["approvedWithoutMove"] == 2
    events = [
        json.loads(line)
        for line in store.history_path.read_text(encoding="utf-8").splitlines()
    ]
    assert events[0]["action"] == "INITIALIZE"
    assert events[-1]["action"] == "GOLD_FINALIZE"


def test_gold_validation_rejects_pending_items_and_categories(tmp_path: Path):
    dataset = make_dataset(tmp_path)
    state = create_review_state(
        "WS-001",
        "테스터",
        dataset,
        "ai_review",
        use_legacy_as_draft=True,
    )
    store = ReviewStore(tmp_path / "review-data", "WS-001")
    store.initialize(state, draft_payload=None)

    errors = store.validate_for_gold(state)

    assert any("미검토" in error for error in errors)
    assert any("승인되지 않은 카테고리" in error for error in errors)
    with pytest.raises(ValueError):
        store.finalize_gold(state, "reviewer-01")


def test_merge_moves_items_and_removes_source_category(tmp_path: Path):
    dataset = make_dataset(tmp_path)
    state = create_review_state(
        "WS-001",
        "테스터",
        dataset,
        "ai_review",
        use_legacy_as_draft=True,
    )
    store = ReviewStore(tmp_path / "review-data", "WS-001")
    store.initialize(state, draft_payload=None)
    source, target = [category["categoryId"] for category in state["categories"]]

    store.merge_category(state, source, target)

    assert len(state["categories"]) == 1
    assert all(item["finalCategoryId"] == target for item in state["items"])


def test_draft_folder_discovery_and_summary(tmp_path: Path):
    dataset = make_dataset(tmp_path)
    draft_folder = tmp_path / "review-inputs" / "WS-001" / "run-001"
    draft_folder.mkdir(parents=True)
    draft_path = draft_folder / "review-draft.jsonl"
    rows = [
        {
            "sourcePath": "학습·지식/0001-url.txt",
            "generatedCategory": "백엔드 개발",
        },
        {
            "sourcePath": "음식·맛집/0002-memo.txt",
            "generatedCategory": "맛집",
        },
    ]
    draft_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows),
        encoding="utf-8",
    )
    (draft_folder / "empty.json").write_text("", encoding="utf-8")

    folders = discover_draft_folders([tmp_path / "review-inputs"])
    files = discover_draft_files(draft_folder)
    payload = read_json_or_jsonl(draft_path)
    summary = summarize_draft(payload, dataset)

    assert folders == [draft_folder.resolve()]
    assert files == [draft_path.resolve()]
    assert summary["ready"] is True
    assert summary["matchedItemCount"] == 2
    assert summary["categoryCount"] == 2


def test_review_conditions_exclude_raw_response_folders(tmp_path: Path):
    group = tmp_path / "results" / "run-001"
    condition = group / "existing11-ai"
    raw = condition / "raw-responses"
    raw.mkdir(parents=True)
    (condition / "review-draft.json").write_text(
        json.dumps({"items": []}), encoding="utf-8"
    )
    (raw / "URL-001.json").write_text(json.dumps({"raw": "value"}), encoding="utf-8")
    (group / "run-summary.json").write_text(json.dumps({"scenarios": []}), encoding="utf-8")

    assert discover_review_conditions(group) == [condition.resolve()]
