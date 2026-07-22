import json

import pytest

from run_classification_experiment import (
    SCENARIO_BY_ID,
    SCENARIOS,
    make_record,
    planned_call_count,
    summarize_scenario,
    write_comparison,
)
from src.metrics import classification_metrics
from src.prompt_builder import build_prompt
from src.response_parser import parse_response


CATEGORIES = ["생활·할 일", "학습·지식", "기타"]


def fake_call(mode: str, parsed: dict, duration: float = 100.0) -> dict:
    return {
        "mode": mode,
        "prompt": "prompt",
        "request": {},
        "ollamaResponse": {},
        "rawResponse": json.dumps(parsed, ensure_ascii=False),
        "parsedResponse": parsed,
        "validation": {
            "jsonValid": True,
            "schemaValid": True,
            "requiredFieldsPresent": True,
            "extraTextDetected": False,
            "thinkingTagDetected": False,
            "validationError": "",
        },
        "evaluation": {},
        "performance": {
            "totalDurationMs": duration,
            "promptEvalCount": 10,
            "evalCount": 5,
        },
        "error": {"requestFailed": False, "errorType": "", "errorMessage": ""},
    }


def memo_item() -> dict:
    return {
        "testId": "TEXT-001",
        "title": "메모",
        "sourcePath": "학습·지식/001-메모.txt",
        "input": "Redis 멱등성을 공부한다.",
        "expected": {
            "categories": ["학습·지식"],
            "requiredKeywords": [],
            "summaryPoints": [],
            "forbiddenClaims": [],
        },
    }


def test_organize_only_schema_combines_summary_tags_and_keywords():
    raw = json.dumps({
        "summary": "Redis 멱등성을 공부한다.",
        "tags": ["Redis", "큐", "멱등성"],
        "keywords": ["재전달", "ACK", "중복 처리"],
    }, ensure_ascii=False)
    parsed = parse_response(raw, CATEGORIES, "organize-only")
    assert parsed["schemaValid"]
    assert "category" not in parsed["parsedResponse"]


def test_category_description_toggle_changes_only_context():
    template = "카테고리:\n{{CATEGORY_DEFINITIONS}}\n{{TITLE_CONTEXT}}{{CONTENT}}"
    definitions = [
        {"name": "학습·지식", "description": "배우고 확인할 지식", "examples": ["Redis 공부"]},
        {"name": "기타", "description": "판단 근거 부족", "examples": ["알 수 없는 문자열"]},
    ]
    names = [item["name"] for item in definitions]
    with_description = build_prompt(
        template, "본문", names, category_definitions=definitions,
        include_category_descriptions=True,
    )
    without_description = build_prompt(
        template, "본문", names, category_definitions=definitions,
        include_category_descriptions=False,
    )
    assert "배우고 확인할 지식" in with_description
    assert "Redis 공부" in with_description
    assert "배우고 확인할 지식" not in without_description
    assert "- 학습·지식" in without_description


@pytest.mark.parametrize("title", ["텍스트-2026.07.20-0905", "텍스트-2026-07-01"])
def test_generated_titles_are_excluded_from_experiment_prompt(title):
    prompt = build_prompt("{{TITLE_CONTEXT}}{{CONTENT}}", "본문", CATEGORIES, title)
    assert title not in prompt


def test_four_scenarios_require_six_calls_per_memo():
    assert planned_call_count(78, 1, list(SCENARIOS)) == 468


def test_invalid_category_prediction_counts_as_false_negative():
    metrics = classification_metrics([
        {"expectedCategory": "학습·지식", "generatedCategory": "학습·지식"},
        {"expectedCategory": "학습·지식", "generatedCategory": ""},
    ], CATEGORIES)
    assert metrics["accuracy"] == pytest.approx(0.5)
    assert metrics["perCategory"]["학습·지식"]["recall"] == pytest.approx(0.5)


def test_integrated_record_counts_one_call():
    integrated = fake_call("integrated", {
        "category": "학습·지식",
        "summary": "Redis 멱등성을 공부한다.",
        "tags": ["Redis", "큐", "멱등성"],
        "keywords": ["재전달", "ACK", "중복 처리"],
    })
    record = make_record(
        SCENARIO_BY_ID["integrated-with-description"],
        memo_item(), 1, None, None, integrated,
    )
    assert record["callCount"] == 1
    assert record["totalDurationMs"] == 100
    assert record["categoryCorrect"]


def test_split_record_sums_two_calls_and_summary():
    category = fake_call("category-only", {"category": "학습·지식", "confidence": 0.9})
    organize = fake_call("organize-only", {
        "summary": "Redis 멱등성을 공부한다.",
        "tags": ["Redis", "큐", "멱등성"],
        "keywords": ["재전달", "ACK", "중복 처리"],
    }, duration=150)
    record = make_record(
        SCENARIO_BY_ID["split-with-description"],
        memo_item(), 1, category, organize, None,
    )
    assert record["callCount"] == 2
    assert record["totalDurationMs"] == 250
    assert record["generatedSummary"] == "Redis 멱등성을 공부한다."


def test_scenario_summary_and_comparison_report(tmp_path):
    category = fake_call("category-only", {"category": "학습·지식", "confidence": 0.9})
    organize = fake_call("organize-only", {
        "summary": "Redis 멱등성을 공부한다.",
        "tags": ["Redis", "큐", "멱등성"],
        "keywords": ["재전달", "ACK", "중복 처리"],
    })
    record = make_record(
        SCENARIO_BY_ID["split-with-description"],
        memo_item(), 1, category, organize, None,
    )
    summaries = []
    for scenario in SCENARIOS:
        scenario_record = record | {
            "scenario": scenario.id,
            "structure": scenario.structure,
            "categoryDescriptions": scenario.category_descriptions,
        }
        if scenario.id == "integrated-without-description":
            scenario_record |= {
                "generatedCategory": "기타",
                "categoryCorrect": False,
                "confidence": None,
            }
        summaries.append(summarize_scenario(scenario, [scenario_record], CATEGORIES))
    write_comparison(tmp_path, summaries)
    assert (tmp_path / "comparison-summary.json").is_file()
    assert (tmp_path / "wrong-answers.csv").is_file()
    report = (tmp_path / "comparison-report.md").read_text(encoding="utf-8")
    assert "분리 방식의 설명 효과" in report
    assert "100.0%" in report
    assert "전체 오답 데이터 (1건)" in report
    assert "TEXT-001" in report
    assert "학습·지식" in report and "기타" in report
