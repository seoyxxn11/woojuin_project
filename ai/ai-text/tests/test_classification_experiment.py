import json

import pytest

import run_classification_experiment as runner
from run_classification_experiment import (
    SCENARIO_BY_ID,
    SCENARIOS,
    evaluate_raw_record,
    make_raw_record,
    planned_call_count,
    resolve_thresholds,
)
from src.prompt_builder import build_prompt
from src.response_parser import parse_response


DEFINITIONS = [
    {"id": "LIFE_TASK", "name": "생활·할 일", "description": "일정", "examples": []},
    {"id": "LEARNING_KNOWLEDGE", "name": "학습·지식", "description": "학습", "examples": []},
    {"id": "TRAVEL_PLACE", "name": "여행·장소", "description": "여행", "examples": []},
    {"id": "FOOD_RESTAURANT", "name": "음식·맛집", "description": "음식", "examples": []},
    {"id": "CULTURE_CONTENT", "name": "문화·콘텐츠", "description": "문화", "examples": []},
    {"id": "OTHER", "name": "기타", "description": "기타", "examples": []},
]
CATEGORIES = [item["name"] for item in DEFINITIONS]
CLASSIFICATION = {
    "fallback_category": "기타", "ensure_at_least_one": True, "service_max_categories": 2,
}
EVALUATION = {
    "gold_mode": "single_label_relaxed",
    "max_allowed_extra_categories": 1, "invalid_prediction_is_wrong": True,
    "fallback_counts_as_model_correct": False,
}


def fake_multi_call(predictions: list[dict], *, integrated: bool = False, summary_valid: bool = True) -> dict:
    parsed = {"categories": predictions}
    if integrated:
        parsed |= {
            "summary": "테스트 요약" if summary_valid else "",
            "tags": ["하나", "둘", "셋"], "keywords": ["하나", "둘", "셋"],
        }
    return {
        "mode": "multi-integrated" if integrated else "multi-category",
        "prompt": "prompt", "request": {}, "ollamaResponse": {},
        "rawResponse": json.dumps(parsed, ensure_ascii=False), "parsedResponse": parsed,
        "parsing": {
            "rawPredictions": predictions, "validPredictions": predictions,
            "invalidPredictions": [], "duplicateCategoryIds": [],
            "categoryParseSuccess": True,
            "summaryParseSuccess": summary_valid if integrated else None,
            "organizationParseSuccess": summary_valid if integrated else None,
        },
        "performance": {"totalDurationMs": 100, "promptEvalCount": 10, "evalCount": 5},
        "error": {"requestFailed": False, "errorType": "", "errorMessage": ""},
    }


def item() -> dict:
    return {
        "testId": "TEXT-001", "title": "제주 맛집", "sourcePath": "여행·장소/001.txt",
        "input": "제주 여행 중 방문할 맛집", "expected": {"categories": ["여행·장소"]},
    }


def raw_record(predictions: list[dict], invalid: list[dict] | None = None) -> dict:
    record = make_raw_record(
        SCENARIO_BY_ID["split-with-description"], item(), 1,
        fake_multi_call(predictions), None, None,
    )
    record["invalidPredictions"] = invalid or []
    return record


def prediction(category_id: str, category_name: str, score: float) -> dict:
    return {"categoryId": category_id, "categoryName": category_name, "score": score}


def test_each_scenario_calls_model_once_and_thresholds_do_not_add_calls():
    assert planned_call_count(78, 1, list(SCENARIOS)) == 312
    config = {"classification": {"threshold": 0.65, "threshold_sweep": {"enabled": True, "values": [0.5, 0.7]}}}
    assert resolve_thresholds(config, None) == [0.5, 0.7]
    assert planned_call_count(78, 1, list(SCENARIOS)) == 312


def test_split_raw_record_contains_one_category_call():
    record = raw_record([prediction("TRAVEL_PLACE", "여행·장소", 0.9)])
    assert record["callCount"] == 1
    assert record["summaryParseSuccess"] is None


def test_integrated_summary_and_category_parse_states_are_independent():
    call = fake_multi_call([prediction("TRAVEL_PLACE", "여행·장소", 0.9)], integrated=True, summary_valid=False)
    record = make_raw_record(
        SCENARIO_BY_ID["integrated-with-description"], item(), 1, None, None, call,
    )
    assert record["categoryParseSuccess"] is True
    assert record["summaryParseSuccess"] is False


def test_threshold_miss_is_separate_from_raw_missing_gold():
    below = evaluate_raw_record(
        raw_record([prediction("TRAVEL_PLACE", "여행·장소", 0.6)]),
        0.7, DEFINITIONS, CLASSIFICATION | {"ensure_at_least_one": False}, EVALUATION,
    )
    missing = evaluate_raw_record(
        raw_record([prediction("FOOD_RESTAURANT", "음식·맛집", 0.9)]),
        0.7, DEFINITIONS, CLASSIFICATION, EVALUATION,
    )
    assert below["thresholdMiss"] is True
    assert "THRESHOLD_MISS" in below["errorTypes"]
    assert missing["thresholdMiss"] is False
    assert "MISSING_GOLD_CATEGORY" in missing["errorTypes"]


def test_fallback_matching_gold_does_not_inflate_model_accuracy():
    result = evaluate_raw_record(
        raw_record([]), 0.7, DEFINITIONS,
        CLASSIFICATION | {"fallback_category": "여행·장소"}, EVALUATION,
    )
    assert result["thresholdSelectedCategoryIds"] == []
    assert result["serviceSelectedCategoryIds"] == ["TRAVEL_PLACE"]
    assert result["fallbackUsed"] is True
    assert result["serviceGoldIncluded"] is True
    assert result["relaxedCorrect"] is False


def test_same_raw_result_is_evaluated_at_multiple_thresholds_without_mutation():
    raw = raw_record([
        prediction("TRAVEL_PLACE", "여행·장소", 0.9),
        prediction("FOOD_RESTAURANT", "음식·맛집", 0.65),
    ])
    low = evaluate_raw_record(raw, 0.6, DEFINITIONS, CLASSIFICATION, EVALUATION)
    high = evaluate_raw_record(raw, 0.7, DEFINITIONS, CLASSIFICATION, EVALUATION)
    assert low["thresholdSelectedCategoryIds"] == ["TRAVEL_PLACE", "FOOD_RESTAURANT"]
    assert high["thresholdSelectedCategoryIds"] == ["TRAVEL_PLACE"]
    assert len(raw["validPredictions"]) == 2


@pytest.mark.parametrize("title", ["텍스트-2026.07.20-0905", "텍스트-2026-07-01"])
def test_generated_titles_are_excluded_from_experiment_prompt(title):
    prompt = build_prompt("{{TITLE_CONTEXT}}{{CONTENT}}", "본문", CATEGORIES, title)
    assert title not in prompt


def test_category_description_toggle_includes_ids_without_description():
    template = "{{CATEGORY_DEFINITIONS}}\n{{TITLE_CONTEXT}}{{CONTENT}}"
    prompt = build_prompt(
        template, "본문", CATEGORIES, category_definitions=DEFINITIONS,
        include_category_descriptions=False,
    )
    assert "TRAVEL_PLACE | 여행·장소" in prompt
    assert "여행" not in prompt.replace("여행·장소", "")


def test_organize_only_response_remains_supported():
    raw = json.dumps({
        "summary": "요약입니다.", "tags": ["하나", "둘", "셋"],
        "keywords": ["넷", "다섯", "여섯"],
    }, ensure_ascii=False)
    assert parse_response(raw, CATEGORIES, "organize-only")["schemaValid"]


def test_evaluate_only_never_constructs_ollama_client(monkeypatch, tmp_path):
    target = tmp_path / "saved"
    raw_path = target / "raw" / "split-with-description" / "results.jsonl"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(json.dumps(raw_record([prediction("TRAVEL_PLACE", "여행·장소", 0.9)]), ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setattr(runner, "OllamaClient", lambda *args: pytest.fail("모델을 호출하면 안 됩니다"))
    code = runner.main([
        "--evaluate-only", "--resume", str(target), "--scenarios", "split-with-description",
        "--thresholds", "0.70", "--limit", "1",
    ])
    assert code == 0
    assert (target / "reports" / "summary.md").is_file()
    report = (target / "reports" / "summary.md").read_text(encoding="utf-8")
    assert "보조 엄격 평가 지표" in report
    assert "최적 조건 판정 상태 분포" in report


def test_resume_skips_completed_model_result(monkeypatch, tmp_path):
    target = tmp_path / "saved"
    raw_path = target / "raw" / "split-with-description" / "results.jsonl"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(json.dumps(raw_record([prediction("TRAVEL_PLACE", "여행·장소", 0.9)]), ensure_ascii=False) + "\n", encoding="utf-8")

    class FakeClient:
        def __init__(self, *args): pass
        def models(self): return ["qwen3:8b"]
        def unload(self, model): pass
        def chat(self, *args): pytest.fail("완료된 원본을 다시 호출하면 안 됩니다")

    monkeypatch.setattr(runner, "OllamaClient", FakeClient)
    code = runner.main([
        "--resume", str(target), "--scenarios", "split-with-description",
        "--thresholds", "0.70", "--test-ids", "TEXT-001",
    ])
    assert code == 0


def test_completed_threshold_evaluation_is_reused(monkeypatch, tmp_path):
    raw = [raw_record([prediction("TRAVEL_PLACE", "여행·장소", 0.9)])]
    config = {"classification": CLASSIFICATION, "evaluation": EVALUATION}
    scenario = SCENARIO_BY_ID["split-with-description"]
    first_rows, _ = runner.evaluate_scenario_threshold(
        tmp_path, scenario, raw, 0.7, DEFINITIONS, config,
    )
    monkeypatch.setattr(
        runner, "evaluate_raw_record",
        lambda *args: pytest.fail("완료된 임계값 평가를 다시 계산하면 안 됩니다"),
    )
    second_rows, _ = runner.evaluate_scenario_threshold(
        tmp_path, scenario, raw, 0.7, DEFINITIONS, config,
    )
    assert second_rows == first_rows
