import json

import pytest

from src.response_parser import parse_multi_label_response


DEFINITIONS = [
    {"id": "TRAVEL_PLACE", "name": "여행·장소"},
    {"id": "FOOD_RESTAURANT", "name": "음식·맛집"},
    {"id": "CULTURE_CONTENT", "name": "문화·콘텐츠"},
]


def parse(value, *, integrated=False):
    raw = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return parse_multi_label_response(raw, DEFINITIONS, integrated=integrated)


def item(category_id="TRAVEL_PLACE", name="여행·장소", score=0.9):
    return {"categoryId": category_id, "categoryName": name, "score": score}


def error_types(result):
    return {error["errorType"] for error in result["invalidPredictions"]}


def test_normal_multi_category_response():
    result = parse({"categories": [item(), item("FOOD_RESTAURANT", "음식·맛집", 0.8)]})
    assert result["categoryParseSuccess"]
    assert [row["categoryId"] for row in result["validPredictions"]] == ["TRAVEL_PLACE", "FOOD_RESTAURANT"]


def test_single_object_is_normalized_to_array():
    result = parse({"categories": item()})
    assert result["singleObjectNormalized"]
    assert len(result["validPredictions"]) == 1


def test_duplicate_category_keeps_highest_score():
    result = parse({"categories": [item(score=0.5), item(score=0.9)]})
    assert result["duplicateCategoryIds"] == ["TRAVEL_PLACE"]
    assert result["validPredictions"][0]["score"] == 0.9


def test_unknown_category_is_invalid():
    result = parse({"categories": [item("UNKNOWN", "없는 분류", 0.9)]})
    assert "INVALID_CATEGORY" in error_types(result)


def test_category_id_name_mismatch_is_invalid_and_id_is_validation_basis():
    result = parse({"categories": [item("TRAVEL_PLACE", "음식·맛집", 0.9)]})
    assert "CATEGORY_ID_NAME_MISMATCH" in error_types(result)
    assert result["validPredictions"] == []


@pytest.mark.parametrize(("score", "expected"), [
    ("0.9", "SCORE_PARSE_ERROR"),
    (None, "SCORE_MISSING"),
    ("", "SCORE_MISSING"),
    (-0.1, "SCORE_OUT_OF_RANGE"),
    (1.1, "SCORE_OUT_OF_RANGE"),
    (float("nan"), "SCORE_PARSE_ERROR"),
])
def test_invalid_scores_are_not_coerced(score, expected):
    result = parse({"categories": [item(score=score)]})
    assert expected in error_types(result)
    assert result["validPredictions"] == []


def test_empty_categories_is_parsed_for_fallback_evaluation():
    result = parse({"categories": []})
    assert result["categoryParseSuccess"]
    assert result["validPredictions"] == []


def test_markdown_and_extra_text_are_detected_but_json_is_parsed():
    result = parse("설명입니다\n```json\n" + json.dumps({"categories": [item()]}, ensure_ascii=False) + "\n```")
    assert result["jsonValid"]
    assert result["markdownCodeBlockDetected"]
    assert result["extraTextDetected"]
    assert result["validPredictions"][0]["categoryId"] == "TRAVEL_PLACE"


def test_legacy_single_category_response_is_compatible():
    result = parse({"category": "여행·장소", "confidence": 0.85})
    assert result["legacySingleCategory"]
    assert result["validPredictions"][0]["categoryId"] == "TRAVEL_PLACE"


def test_categories_take_priority_when_legacy_category_also_exists():
    result = parse({
        "category": "음식·맛집", "confidence": 0.99,
        "categories": [item()],
    })
    assert result["legacyCategoryIgnored"]
    assert [row["categoryId"] for row in result["validPredictions"]] == ["TRAVEL_PLACE"]


def test_integrated_summary_failure_does_not_fail_category_parsing():
    result = parse({
        "summary": "", "tags": ["가", "나", "다"], "keywords": ["라", "마", "바"],
        "categories": [item()],
    }, integrated=True)
    assert result["summaryParseSuccess"] is False
    assert result["categoryParseSuccess"] is True


def test_integrated_category_failure_does_not_fail_summary_parsing():
    result = parse({
        "summary": "유효한 요약입니다.", "tags": ["가", "나", "다"], "keywords": ["라", "마", "바"],
        "categories": [item(score="잘못된 점수")],
    }, integrated=True)
    assert result["summaryParseSuccess"] is True
    assert result["categoryParseSuccess"] is False
