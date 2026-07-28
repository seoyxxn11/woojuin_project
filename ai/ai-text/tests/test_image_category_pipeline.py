from __future__ import annotations

import json
from pathlib import Path

from run_image_category_test import (
    classification_content,
    image_metadata,
    image_result,
    keyword_recall,
    load_answer_key,
    select_service_categories,
)


def test_classification_content_omits_empty_ocr() -> None:
    content = classification_content(
        {
            "title": "초밥",
            "description": "모둠 초밥 한 접시",
            "tags": ["초밥", "연어"],
            "ocr_text": "",
            "objects": ["접시"],
        }
    )
    assert "OCR 텍스트" not in content
    assert "태그: 초밥, 연어" in content


def test_failed_image_record_is_excluded() -> None:
    assert image_result({"json_valid": False, "result": None, "error": "failed"}) is None


def test_image_metadata_preserves_only_service_exif() -> None:
    assert image_metadata(
        {
            "metadata": {
                "latitude": 35.1,
                "longitude": 126.8,
                "captured_at": "2026-07-28T12:00:00",
                "latency_ms": 1000,
            }
        }
    ) == {
        "latitude": 35.1,
        "longitude": 126.8,
        "captured_at": "2026-07-28T12:00:00",
    }


def test_answer_key_is_loaded_separately(tmp_path: Path) -> None:
    path = tmp_path / "answers.jsonl"
    path.write_text(
        json.dumps({"id": "sample-1", "category": "음식·맛집"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    assert load_answer_key(path) == {
        "sample-1": {
            "category": "음식·맛집",
            "acceptable_categories": ["음식·맛집"],
            "required_concepts": [],
            "ocr_keywords": [],
        }
    }


def test_keyword_recall_accepts_alternative_expressions() -> None:
    hits, total, recall = keyword_recall(
        [["돈가스덮밥", "가츠동"], ["계란", "달걀"]],
        "가츠동 위에 달걀이 올라가 있다.",
    )
    assert (hits, total, recall) == (2, 2, 1.0)


def test_secondary_category_requires_score_and_small_gap() -> None:
    close = [
        {"categoryName": "여행·장소", "score": 0.55},
        {"categoryName": "음식·맛집", "score": 0.48},
    ]
    far = [
        {"categoryName": "여행·장소", "score": 0.80},
        {"categoryName": "음식·맛집", "score": 0.60},
    ]
    assert [item["categoryName"] for item in select_service_categories(close)] == [
        "여행·장소", "음식·맛집"
    ]
    assert [item["categoryName"] for item in select_service_categories(far)] == ["여행·장소"]
