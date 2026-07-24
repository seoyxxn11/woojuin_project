from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.dataset_loader import load_categories, load_category_definitions, load_memo_dataset
from src.multi_label_selector import category_maps, resolve_category_id, select_categories
from src.ollama_client import OllamaClient, OllamaError, performance
from src.prompt_builder import build_prompt, load_prompt
from src.relaxed_evaluator import (
    RelaxedEvaluationStatus,
    evaluate_single_gold_relaxed,
    summarize_threshold_rows,
)
from src.response_parser import (
    output_multi_label_schema,
    output_schema,
    parse_multi_label_response,
    parse_response,
)
from src.result_writer import append_jsonl, read_jsonl, write_csv, write_json


ROOT = Path(__file__).resolve().parent
MODEL = "qwen3:8b"
RESULTS_ROOT = ROOT / "results" / "4차 다중 카테고리 분류 비교"
PROMPT_VERSION = "multi-label-v1"
EVALUATION_VERSION = "single-gold-relaxed-v1"


@dataclass(frozen=True)
class Scenario:
    id: str
    structure: str
    category_descriptions: bool
    calls_per_item: int


SCENARIOS = (
    Scenario("split-with-description", "split", True, 1),
    Scenario("split-without-description", "split", False, 1),
    Scenario("integrated-with-description", "integrated", True, 1),
    Scenario("integrated-without-description", "integrated", False, 1),
)
SCENARIO_BY_ID = {scenario.id: scenario for scenario in SCENARIOS}
PROMPT_FILES = {
    "category": "experiment-category-prompt-v1.txt",
    "organize": "experiment-organize-prompt-v1.txt",
    "integrated": "experiment-integrated-prompt-v1.txt",
}
DETAILED_CSV_FIELDS = (
    "id", "testId", "scenario", "structure", "categoryDescriptions", "repeatNumber",
    "title", "sourcePath", "expectedCategoryId", "expectedCategoryName", "top1CategoryId",
    "top1Correct", "threshold", "thresholdSelectedCategoryIds", "serviceSelectedCategoryIds",
    "goldIncluded", "extraCategoryIds", "extraCategoryCount", "selectedCategoryCount",
    "exactCorrect", "relaxedCorrect", "evaluationStatus", "overPrediction", "missingGold",
    "thresholdMiss", "fallbackUsed", "ensureAtLeastOneUsed", "serviceLimitApplied",
    "rawGoldPresent", "serviceGoldIncluded", "serviceExactCorrect", "serviceRelaxedCorrect",
    "hasInvalidPrediction", "invalidPredictions", "errorTypes", "rawPredictions",
    "validPredictions", "categoryParseSuccess", "summaryParseSuccess",
    "organizationParseSuccess", "requestFailed", "totalDurationMs",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="qwen3:8b 다중 카테고리 적합도 및 단일 정답 완화 평가 실험"
    )
    parser.add_argument("--repeat", type=int, default=1, help="메모별 반복 횟수 (기본 1)")
    parser.add_argument("--limit", type=int, help="앞에서부터 실행할 메모 수")
    parser.add_argument("--test-ids", nargs="+", help="실행할 TEXT-001 형식의 ID")
    parser.add_argument(
        "--scenarios", nargs="+", choices=tuple(SCENARIO_BY_ID),
        help="일부 조건만 실행. 생략하면 네 조건 모두 실행",
    )
    parser.add_argument("--thresholds", nargs="+", type=float, help="설정 대신 평가할 임계값 목록")
    parser.add_argument(
        "--category-definitions",
        help="config/categories.json 대신 사용할 카테고리 정의 JSON",
    )
    parser.add_argument("--resume", help="기존 결과 상위 폴더를 지정해 이어서 실행")
    parser.add_argument("--evaluate-only", action="store_true", help="저장된 원본 응답만 임계값 재평가")
    parser.add_argument("--dry-run", action="store_true", help="모델 호출과 결과 저장 없이 계획만 확인")
    return parser.parse_args(argv)


def model_installed(wanted: str, installed: list[str]) -> bool:
    return wanted in installed or any(name.split(":")[0] == wanted for name in installed)


def load_experiment_data(options: argparse.Namespace) -> tuple[list[dict], list[str], list[dict]]:
    memo_root = ROOT / "dataset" / "memo"
    folder_categories = load_categories(memo_root)
    definitions_path = (
        Path(options.category_definitions).resolve()
        if options.category_definitions else ROOT / "config" / "categories.json"
    )
    definitions = load_category_definitions(definitions_path, memo_root)
    categories = [str(item["name"]) for item in definitions]
    if set(categories) != set(folder_categories):
        raise ValueError("카테고리 정의와 메모 폴더가 일치하지 않습니다")
    data = load_memo_dataset(memo_root, categories)
    if options.test_ids:
        requested = set(options.test_ids)
        unknown = requested - {item["testId"] for item in data}
        if unknown:
            raise ValueError(f"없는 testId: {sorted(unknown)}")
        data = [item for item in data if item["testId"] in requested]
    if options.limit is not None:
        if options.limit < 1:
            raise ValueError("--limit는 1 이상이어야 합니다")
        data = data[:options.limit]
    if not data:
        raise ValueError("실행할 메모가 없습니다")
    return data, categories, definitions


def selected_scenarios(options: argparse.Namespace) -> list[Scenario]:
    ids = options.scenarios or [scenario.id for scenario in SCENARIOS]
    return [SCENARIO_BY_ID[scenario_id] for scenario_id in ids]


def planned_call_count(data_count: int, repeat: int, scenarios: list[Scenario]) -> int:
    return data_count * repeat * sum(scenario.calls_per_item for scenario in scenarios)


def resolve_thresholds(config: dict[str, Any], cli_values: list[float] | None) -> list[float]:
    classification = config["classification"]
    if cli_values:
        values = cli_values
    elif classification.get("threshold_sweep", {}).get("enabled"):
        values = classification["threshold_sweep"].get("values", [])
    else:
        values = [classification["threshold"]]
    thresholds = sorted({float(value) for value in values})
    if not thresholds or any(not 0 <= value <= 1 for value in thresholds):
        raise ValueError("임계값은 0 이상 1 이하의 숫자여야 합니다")
    return thresholds


def validate_config(config: dict[str, Any], definitions: list[dict[str, Any]]) -> None:
    classification = config.get("classification", {})
    evaluation = config.get("evaluation", {})
    if classification.get("mode") not in {"single_label", "multi_label"}:
        raise ValueError("classification.mode는 single_label 또는 multi_label이어야 합니다")
    if evaluation.get("gold_mode") not in {"single_label_relaxed", "multi_label_strict"}:
        raise ValueError("지원하지 않는 evaluation.gold_mode입니다")
    if evaluation.get("gold_mode") != "single_label_relaxed":
        raise ValueError("현재 실험은 single_label_relaxed 평가만 실행할 수 있습니다")
    if int(evaluation.get("max_allowed_extra_categories", -1)) < 0:
        raise ValueError("max_allowed_extra_categories는 0 이상이어야 합니다")
    resolve_category_id(str(classification.get("fallback_category", "")), definitions)
    if int(classification.get("service_max_categories", 0)) < 1:
        raise ValueError("service_max_categories는 1 이상이어야 합니다")


def unique_output_dir() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = RESULTS_ROOT / timestamp
    suffix = 1
    while candidate.exists():
        candidate = RESULTS_ROOT / f"{timestamp}-{suffix}"
        suffix += 1
    return candidate


def dataset_fingerprint(data: list[dict[str, Any]]) -> str:
    payload = [
        {"testId": item["testId"], "title": item.get("title", ""), "input": item["input"], "expected": item["expected"]}
        for item in data
    ]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def model_run_identifier(scenario: Scenario, data_fingerprint: str) -> str:
    payload = {
        "model": MODEL, "structure": scenario.structure,
        "categoryDescriptions": scenario.category_descriptions,
        "classificationMode": "multi_label", "promptVersion": PROMPT_VERSION,
        "datasetFingerprint": data_fingerprint,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"{scenario.id}-{digest}"


def _base_call(mode: str, prompt: str) -> dict[str, Any]:
    return {
        "mode": mode, "prompt": prompt, "request": {}, "ollamaResponse": {},
        "rawResponse": "", "parsedResponse": None, "parsing": {}, "performance": {},
        "error": {"requestFailed": False, "errorType": "", "errorMessage": ""},
    }


def invoke_multi(
    client: OllamaClient,
    config: dict[str, Any],
    prompt: str,
    definitions: list[dict[str, Any]],
    *,
    integrated: bool,
) -> dict[str, Any]:
    mode = "multi-integrated" if integrated else "multi-category"
    call = _base_call(mode, prompt)
    try:
        request, response = client.chat(
            MODEL, prompt, config["temperature"], config["keepAlive"],
            output_multi_label_schema(definitions, integrated), config.get("seed"),
            config.get("contextLength"), config.get("thinking"),
        )
        raw = str(response.get("message", {}).get("content", ""))
        parsing = parse_multi_label_response(raw, definitions, integrated=integrated)
        call.update({
            "request": request,
            "ollamaResponse": _ollama_metadata(response),
            "rawResponse": raw,
            "parsedResponse": parsing.get("parsedResponse"),
            "parsing": parsing,
            "performance": performance(response),
        })
        if not raw.strip():
            call["error"] = {"requestFailed": True, "errorType": "EMPTY_RESPONSE", "errorMessage": "빈 응답"}
        elif not parsing["jsonValid"]:
            call["error"] = {
                "requestFailed": True, "errorType": "INVALID_JSON",
                "errorMessage": parsing.get("validationError", ""),
            }
    except OllamaError as exc:
        call["error"] = {"requestFailed": True, "errorType": exc.error_type, "errorMessage": str(exc)}
    return call


def invoke_organize(
    client: OllamaClient,
    config: dict[str, Any],
    prompt: str,
    categories: list[str],
) -> dict[str, Any]:
    call = _base_call("organize-only", prompt)
    try:
        request, response = client.chat(
            MODEL, prompt, config["temperature"], config["keepAlive"],
            output_schema(categories, "organize-only"), config.get("seed"),
            config.get("contextLength"), config.get("thinking"),
        )
        raw = str(response.get("message", {}).get("content", ""))
        parsing = parse_response(raw, categories, "organize-only")
        call.update({
            "request": request, "ollamaResponse": _ollama_metadata(response),
            "rawResponse": raw, "parsedResponse": parsing.get("parsedResponse"),
            "parsing": parsing, "performance": performance(response),
        })
        if not raw.strip() or not parsing["jsonValid"]:
            call["error"] = {
                "requestFailed": True,
                "errorType": "EMPTY_RESPONSE" if not raw.strip() else "INVALID_JSON",
                "errorMessage": parsing.get("validationError", ""),
            }
    except OllamaError as exc:
        call["error"] = {"requestFailed": True, "errorType": exc.error_type, "errorMessage": str(exc)}
    return call


def _ollama_metadata(response: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "model", "created_at", "done", "done_reason", "total_duration", "load_duration",
        "prompt_eval_count", "prompt_eval_duration", "eval_count", "eval_duration",
    )
    return {key: response.get(key) for key in keys}


def _sum_call_metric(calls: list[dict[str, Any]], key: str) -> float:
    return sum(float(call.get("performance", {}).get(key, 0) or 0) for call in calls)


def make_raw_record(
    scenario: Scenario,
    item: dict[str, Any],
    repeat_number: int,
    category_call: dict[str, Any] | None,
    organize_call: dict[str, Any] | None,
    integrated_call: dict[str, Any] | None,
) -> dict[str, Any]:
    calls = [integrated_call] if integrated_call is not None else [category_call]
    calls = [call for call in calls if call is not None]
    category_source = integrated_call if integrated_call is not None else category_call
    organize_source = integrated_call if integrated_call is not None else organize_call
    if category_source is None:
        raise ValueError("분류 호출 결과가 누락됐습니다")
    category_parsing = category_source.get("parsing") or {}
    organize_parsed = organize_source.get("parsedResponse") or {} if organize_source else {}
    if integrated_call is not None:
        summary_success = category_parsing.get("summaryParseSuccess")
        organization_success = category_parsing.get("organizationParseSuccess")
    elif organize_source is not None:
        organize_parsing = organize_source.get("parsing") or {}
        summary_success = bool(organize_parsing.get("schemaValid"))
        organization_success = bool(organize_parsing.get("schemaValid"))
    else:
        summary_success = None
        organization_success = None
    expected = item.get("expected", {})
    expected_names = expected.get("categories") or ([expected["category"]] if expected.get("category") else [])
    if not expected_names:
        raise ValueError(f"{item['testId']}: 단일 정답 카테고리가 없습니다")
    return {
        "testId": item["testId"], "title": item.get("title", ""),
        "sourcePath": item.get("sourcePath", ""), "input": item["input"],
        "expectedCategoryName": expected_names[0],
        "scenario": scenario.id, "structure": scenario.structure,
        "categoryDescriptions": scenario.category_descriptions, "model": MODEL,
        "repeatNumber": repeat_number,
        "rawPredictions": category_parsing.get("rawPredictions", []),
        "validPredictions": category_parsing.get("validPredictions", []),
        "invalidPredictions": category_parsing.get("invalidPredictions", []),
        "duplicateCategoryIds": category_parsing.get("duplicateCategoryIds", []),
        "categoryParseSuccess": bool(category_parsing.get("categoryParseSuccess")),
        "summaryParseSuccess": summary_success,
        "organizationParseSuccess": organization_success,
        "generatedSummary": organize_parsed.get("summary", ""),
        "generatedTags": organize_parsed.get("tags", []),
        "generatedKeywords": organize_parsed.get("keywords", []),
        "requestFailed": any(call["error"]["requestFailed"] for call in calls),
        "callCount": len(calls), "totalDurationMs": _sum_call_metric(calls, "totalDurationMs"),
        "promptTokenCount": int(_sum_call_metric(calls, "promptEvalCount")),
        "outputTokenCount": int(_sum_call_metric(calls, "evalCount")),
        "categoryCall": category_call, "organizeCall": organize_call,
        "integratedCall": integrated_call,
        "executedAt": datetime.now().astimezone().isoformat(),
    }


def evaluate_raw_record(
    raw_record: dict[str, Any],
    threshold: float,
    definitions: list[dict[str, Any]],
    classification_config: dict[str, Any],
    evaluation_config: dict[str, Any],
) -> dict[str, Any]:
    _, by_name = category_maps(definitions)
    gold_name = str(raw_record["expectedCategoryName"])
    gold_id = str(by_name[gold_name]["id"])
    fallback_id = resolve_category_id(str(classification_config["fallback_category"]), definitions)
    valid_predictions = list(raw_record.get("validPredictions", []))
    invalid_predictions = list(raw_record.get("invalidPredictions", []))
    selection = select_categories(
        valid_predictions, threshold=threshold,
        ensure_at_least_one=bool(classification_config["ensure_at_least_one"]),
        fallback_category_id=fallback_id,
        service_max_categories=int(classification_config["service_max_categories"]),
    )
    selected_ids = list(selection["thresholdSelectedCategoryIds"])
    invalid_for_evaluation = invalid_predictions if evaluation_config.get("invalid_prediction_is_wrong", True) else []
    status = evaluate_single_gold_relaxed(
        gold_id, selected_ids, invalid_for_evaluation,
        int(evaluation_config["max_allowed_extra_categories"]),
    )
    selected_set = set(selected_ids)
    service_set = set(selection["serviceSelectedCategoryIds"])
    extras = sorted(selected_set - {gold_id})
    service_extras = service_set - {gold_id}
    max_extras = int(evaluation_config["max_allowed_extra_categories"])
    gold_in_raw = any(item["categoryId"] == gold_id for item in valid_predictions)
    threshold_miss = gold_in_raw and gold_id not in selected_set
    top1_id = valid_predictions[0]["categoryId"] if valid_predictions else None
    fallback_counts = bool(evaluation_config.get("fallback_counts_as_model_correct", False))
    relaxed_correct = status in {
        RelaxedEvaluationStatus.EXACT_CORRECT, RelaxedEvaluationStatus.RELAXED_CORRECT,
    } and (fallback_counts or not selection["fallbackUsed"])
    error_types = [str(item.get("errorType", "INVALID_CATEGORY")) for item in invalid_predictions]
    if not gold_in_raw:
        error_types.append("MISSING_GOLD_CATEGORY")
    if gold_id in selected_set and len(extras) > max_extras:
        error_types.append("OVER_PREDICTION")
    if not selected_ids:
        error_types.append("EMPTY_PREDICTION")
    if threshold_miss:
        error_types.append("THRESHOLD_MISS")
    if selection["fallbackUsed"]:
        error_types.append("FALLBACK_USED")
    error_types = list(dict.fromkeys(filter(None, error_types)))
    numeric_id = int(str(raw_record["testId"]).split("-")[-1])
    return {
        "id": numeric_id, "testId": raw_record["testId"], "title": raw_record.get("title", ""),
        "sourcePath": raw_record.get("sourcePath", ""), "input": raw_record.get("input", ""),
        "scenario": raw_record["scenario"], "structure": raw_record["structure"],
        "categoryDescriptions": raw_record["categoryDescriptions"],
        "repeatNumber": raw_record["repeatNumber"], "model": raw_record["model"],
        "expectedCategoryId": gold_id, "expectedCategoryName": gold_name,
        "top1CategoryId": top1_id, "top1Correct": top1_id == gold_id,
        "rawPredictions": raw_record.get("rawPredictions", []),
        "validPredictions": valid_predictions, "invalidPredictions": invalid_predictions,
        **selection,
        "goldIncluded": gold_id in selected_set,
        "rawGoldPresent": gold_in_raw,
        "extraCategoryIds": extras, "extraCategoryCount": len(extras),
        "selectedCategoryCount": len(selected_ids),
        "exactCorrect": status == RelaxedEvaluationStatus.EXACT_CORRECT and not selection["fallbackUsed"],
        "relaxedCorrect": relaxed_correct, "evaluationStatus": status.value,
        "overPrediction": gold_id in selected_set and len(extras) > max_extras,
        "missingGold": gold_id not in selected_set,
        "thresholdMiss": threshold_miss, "hasInvalidPrediction": bool(invalid_predictions),
        "modelCorrectBeforeFallback": relaxed_correct,
        "serviceGoldIncluded": gold_id in service_set,
        "serviceExactCorrect": service_set == {gold_id},
        "serviceRelaxedCorrect": gold_id in service_set and len(service_extras) <= max_extras,
        "errorTypes": error_types,
        "categoryParseSuccess": raw_record.get("categoryParseSuccess"),
        "summaryParseSuccess": raw_record.get("summaryParseSuccess"),
        "organizationParseSuccess": raw_record.get("organizationParseSuccess"),
        "requestFailed": raw_record.get("requestFailed"),
        "totalDurationMs": raw_record.get("totalDurationMs"),
        "generatedSummary": raw_record.get("generatedSummary", ""),
        "generatedTags": raw_record.get("generatedTags", []),
        "generatedKeywords": raw_record.get("generatedKeywords", []),
    }


def _average(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return statistics.mean(values) if values else None


def score_distribution(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    gold_scores: list[float] = []
    top1_wrong_scores: list[float] = []
    extra_scores: list[float] = []
    near_threshold_misses: list[dict[str, Any]] = []
    for row in rows:
        gold_id = row["expectedCategoryId"]
        by_id = {item["categoryId"]: item for item in row.get("validPredictions", [])}
        if gold_id in by_id:
            score = float(by_id[gold_id]["score"])
            gold_scores.append(score)
            if row["thresholdMiss"] and abs(score - threshold) <= 0.05:
                near_threshold_misses.append({"testId": row["testId"], "score": score})
        if not row["top1Correct"] and row.get("validPredictions"):
            top1_wrong_scores.append(float(row["validPredictions"][0]["score"]))
        extra_scores.extend(
            float(by_id[category_id]["score"])
            for category_id in row.get("extraCategoryIds", []) if category_id in by_id
        )
    mean = lambda values: statistics.mean(values) if values else None
    return {
        "averageGoldCategoryScore": mean(gold_scores),
        "averageWrongTop1Score": mean(top1_wrong_scores),
        "averageExtraCategoryScore": mean(extra_scores),
        "nearThresholdGoldMisses": near_threshold_misses,
    }


def flatten_detailed(row: dict[str, Any]) -> dict[str, Any]:
    result = {key: row.get(key) for key in DETAILED_CSV_FIELDS}
    for key in ("thresholdSelectedCategoryIds", "serviceSelectedCategoryIds", "extraCategoryIds", "errorTypes"):
        result[key] = "|".join(map(str, row.get(key, [])))
    for key in ("rawPredictions", "validPredictions", "invalidPredictions"):
        result[key] = json.dumps(row.get(key, []), ensure_ascii=False, separators=(",", ":"))
    return result


def evaluation_fingerprint(
    raw_records: list[dict[str, Any]], threshold: float,
    classification_config: dict[str, Any], evaluation_config: dict[str, Any],
) -> str:
    payload = {
        "keys": [(row["testId"], row["repeatNumber"], row.get("rawPredictions")) for row in raw_records],
        "threshold": threshold, "classification": classification_config, "evaluation": evaluation_config,
        "evaluationVersion": EVALUATION_VERSION,
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def evaluate_scenario_threshold(
    output: Path,
    scenario: Scenario,
    raw_records: list[dict[str, Any]],
    threshold: float,
    definitions: list[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    threshold_name = f"{threshold:.2f}"
    target = output / "threshold" / scenario.id / threshold_name
    fingerprint = evaluation_fingerprint(raw_records, threshold, config["classification"], config["evaluation"])
    metadata_path = target / "evaluation-metadata.json"
    rows_path = target / "evaluation-results.json"
    metrics_path = target / "metrics.json"
    if metadata_path.exists() and rows_path.exists() and metrics_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("fingerprint") == fingerprint:
            return (
                json.loads(rows_path.read_text(encoding="utf-8")),
                json.loads(metrics_path.read_text(encoding="utf-8")),
            )
    rows = [
        evaluate_raw_record(record, threshold, definitions, config["classification"], config["evaluation"])
        for record in raw_records
    ]
    category_ids = [str(item["id"]) for item in definitions]
    metrics = summarize_threshold_rows(rows, category_ids) | {
        "scenario": scenario.id, "structure": scenario.structure,
        "categoryDescriptions": scenario.category_descriptions, "threshold": threshold,
        "averageTotalDurationMs": _average(raw_records, "totalDurationMs"),
        "averageCallsPerResult": _average(raw_records, "callCount"),
        "categoryParseSuccessRate": (
            sum(bool(row.get("categoryParseSuccess")) for row in raw_records) / len(raw_records)
            if raw_records else None
        ),
        "summaryParseSuccessRate": (
            sum(bool(row.get("summaryParseSuccess")) for row in raw_records) / len(raw_records)
            if raw_records else None
        ),
        "scoreDistribution": score_distribution(rows, threshold),
    }
    write_json(rows_path, rows)
    write_csv(target / "evaluation-results.csv", [flatten_detailed(row) for row in rows], list(DETAILED_CSV_FIELDS))
    write_json(metrics_path, metrics)
    write_json(metadata_path, {
        "fingerprint": fingerprint,
        "evaluationId": f"{scenario.id}-{threshold:.2f}-{fingerprint[:16]}",
        "modelRunId": raw_records[0].get("modelRunId", scenario.id) if raw_records else scenario.id,
        "threshold": threshold, "evaluationMode": config["evaluation"]["gold_mode"],
        "evaluationVersion": EVALUATION_VERSION,
        "maxAllowedExtraCategories": config["evaluation"]["max_allowed_extra_categories"],
    })
    return rows, metrics


def best_metrics(metrics_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not metrics_rows:
        return None
    def value(row: dict[str, Any], key: str, default: float) -> float:
        raw = row.get(key)
        return float(raw) if raw is not None else default
    return max(metrics_rows, key=lambda row: (
        value(row, "relaxedAccuracy", -1), value(row, "top1Accuracy", -1),
        value(row, "exactAccuracy", -1), value(row, "goldCoverage", -1),
        -value(row, "overPredictionRate", 1), -value(row, "averageExtraCategoryCount", 999),
        -value(row, "averageTotalDurationMs", float("inf")),
    ))


def _display(value: Any, percent: bool = False) -> str:
    if value is None:
        return "N/A"
    return f"{float(value) * 100:.1f}%" if percent else f"{float(value):.3f}"


def write_reports(
    output: Path,
    metrics_rows: list[dict[str, Any]],
    detailed_rows: list[dict[str, Any]],
) -> None:
    reports = output / "reports"
    best = best_metrics(metrics_rows)
    write_csv(reports / "threshold-comparison.csv", metrics_rows)
    lines = ["# qwen3:8b 다중 카테고리 분류 비교", ""]
    if best:
        lines += [
            "## 전체 요약", "",
            f"- 최적 처리 구조: {best['structure']}",
            f"- 카테고리 설명 포함 여부: {'포함' if best['categoryDescriptions'] else '미포함'}",
            f"- 최적 임계값: {best['threshold']:.2f}",
            f"- Relaxed Accuracy: {_display(best['relaxedAccuracy'], True)}",
            f"- Top-1 Accuracy: {_display(best['top1Accuracy'], True)}",
            f"- Exact Accuracy: {_display(best['exactAccuracy'], True)}",
            f"- Gold Coverage: {_display(best['goldCoverage'], True)}",
            f"- Over-prediction Rate: {_display(best['overPredictionRate'], True)}",
            f"- 평균 예측 카테고리 수: {_display(best['averageSelectedCategoryCount'])}",
            f"- 평균 추가 카테고리 수: {_display(best['averageExtraCategoryCount'])}",
            f"- 평균 처리 시간: {_display(best['averageTotalDurationMs'])}ms", "",
            "### 원본·임계값·서비스 결과 분리", "",
            f"- 모델 원본 Top-1 Accuracy: {_display(best['top1Accuracy'], True)}",
            f"- 모델 원본 Gold Presence Rate: {_display(best['rawGoldPresenceRate'], True)}",
            f"- 임계값 적용 Relaxed Accuracy: {_display(best['relaxedAccuracy'], True)}",
            f"- 임계값 적용 Exact Accuracy: {_display(best['exactAccuracy'], True)}",
            f"- fallback·최대 개수 적용 서비스 Gold Coverage: {_display(best['serviceGoldCoverage'], True)}",
            f"- fallback·최대 개수 적용 서비스 Exact Accuracy: {_display(best['serviceExactAccuracy'], True)}",
            f"- fallback·최대 개수 적용 서비스 Relaxed Accuracy: {_display(best['serviceRelaxedAccuracy'], True)}", "",
        ]
    lines += [
        "## 임계값 비교", "",
        "| 처리 구조 | 설명 포함 | 임계값 | Top-1 Accuracy | Exact Accuracy | Relaxed Accuracy | Gold Coverage | Over-prediction Rate | 평균 예측 수 | 처리 시간(ms) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metrics_rows:
        lines.append(
            f"| {row['structure']} | {'예' if row['categoryDescriptions'] else '아니오'} | {row['threshold']:.2f} | "
            f"{_display(row['top1Accuracy'], True)} | {_display(row['exactAccuracy'], True)} | "
            f"{_display(row['relaxedAccuracy'], True)} | {_display(row['goldCoverage'], True)} | "
            f"{_display(row['overPredictionRate'], True)} | {_display(row['averageSelectedCategoryCount'])} | "
            f"{_display(row['averageTotalDurationMs'])} |"
        )
    lines += [
        "", "## 보조 엄격 평가 지표", "",
        "| 조건 | 임계값 | Missing Gold | 평균 추가 수 | Threshold Miss | Invalid | Fallback | Strict Micro F1 | Strict Macro F1 | Hamming Loss | Jaccard |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metrics_rows:
        lines.append(
            f"| {row['scenario']} | {row['threshold']:.2f} | {_display(row['missingGoldRate'], True)} | "
            f"{_display(row['averageExtraCategoryCount'])} | {_display(row['thresholdMissRate'], True)} | "
            f"{_display(row['invalidPredictionRate'], True)} | {_display(row['fallbackUsageRate'], True)} | "
            f"{_display(row['strictMicroF1'], True)} | {_display(row['strictMacroF1'], True)} | "
            f"{_display(row['hammingLoss'])} | {_display(row['jaccardScore'])} |"
        )
    if best:
        lines += ["", "## 최적 조건 판정 상태 분포", ""]
        for status, distribution in best["statusDistribution"].items():
            lines.append(
                f"- {status}: {distribution['count']}건 ({_display(distribution['rate'], True)})"
            )
        score_distribution = best["scoreDistribution"]
        lines += [
            "", "## 최적 조건 카테고리 적합도 분포", "",
            f"- 정답 카테고리 적합도 평균: {_display(score_distribution['averageGoldCategoryScore'])}",
            f"- Top-1 오답 카테고리 적합도 평균: {_display(score_distribution['averageWrongTop1Score'])}",
            f"- 추가 카테고리 적합도 평균: {_display(score_distribution['averageExtraCategoryScore'])}",
            f"- 임계값 ±0.05 구간 정답 누락: {len(score_distribution['nearThresholdGoldMisses'])}건",
        ]
    lines += [
        "", "## 평가 해석", "",
        "- 적합도 점수는 모델이 판단한 카테고리 관련성 수치이며 통계적으로 보정된 값으로 해석하지 않습니다.",
        "- 현재 주 평가 순서는 Relaxed Accuracy, Top-1 Accuracy, Exact Accuracy, Gold Coverage, Over-prediction Rate입니다.",
        "- 엄격 다중 라벨 지표는 추가 예측을 false positive로 처리하는 보조 지표입니다.",
        "", "## 현재 평가 방식의 한계", "",
        "현재 테스트 데이터에는 정답 카테고리가 하나만 존재하므로, 정답과 함께 반환된 추가 카테고리가 실제로 적합한지 완전히 검증할 수 없습니다.",
        "따라서 추가 카테고리 1개까지 허용하는 Relaxed Accuracy는 정식 다중 라벨 정확도가 아니라 단일 정답 데이터 기반 완화 지표입니다.", "",
    ]
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    errors = [row for row in detailed_rows if not row["relaxedCorrect"] or row["errorTypes"]]
    error_lines = [
        "# 다중 카테고리 오류 분석", "",
        "| 조건 | 임계값 | ID | 정답 | 선택 | 상태 | 오류 유형 |",
        "|---|---:|---|---|---|---|---|",
    ]
    for row in errors:
        error_lines.append(
            f"| {row['scenario']} | {row['threshold']:.2f} | {row['testId']} | "
            f"{row['expectedCategoryId']} | {' / '.join(row['thresholdSelectedCategoryIds']) or '없음'} | "
            f"{row['evaluationStatus']} | {' / '.join(row['errorTypes']) or '없음'} |"
        )
    (reports / "error-analysis.md").write_text("\n".join(error_lines) + "\n", encoding="utf-8")


def finalize(
    output: Path,
    scenarios: list[Scenario],
    thresholds: list[float],
    definitions: list[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_detailed: list[dict[str, Any]] = []
    all_metrics: list[dict[str, Any]] = []
    for scenario in scenarios:
        raw_path = output / "raw" / scenario.id / "results.jsonl"
        raw_records = read_jsonl(raw_path) if raw_path.exists() else []
        for threshold in thresholds:
            rows, metrics = evaluate_scenario_threshold(
                output, scenario, raw_records, threshold, definitions, config,
            )
            all_detailed.extend(rows)
            all_metrics.append(metrics)
    write_json(output / "json" / "detailed-results.json", all_detailed)
    write_csv(
        output / "csv" / "detailed-results.csv",
        [flatten_detailed(row) for row in all_detailed], list(DETAILED_CSV_FIELDS),
    )
    write_reports(output, all_metrics, all_detailed)
    return all_detailed, all_metrics


def main(argv: list[str] | None = None) -> int:
    options = parse_args(argv)
    if options.repeat < 1:
        print("[FAIL] --repeat는 1 이상이어야 합니다")
        return 2
    if options.evaluate_only and not options.resume:
        print("[FAIL] --evaluate-only에는 --resume 결과 폴더가 필요합니다")
        return 2
    if sys.version_info < (3, 11):
        print("[FAIL] Python 3.11 이상이 필요합니다")
        return 2
    try:
        data, categories, definitions = load_experiment_data(options)
        config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8")) or {}
        validate_config(config, definitions)
        thresholds = resolve_thresholds(config, options.thresholds)
    except (OSError, ValueError, KeyError) as exc:
        print(f"[FAIL] 설정 또는 데이터 검증 실패: {exc}")
        return 2
    scenarios = selected_scenarios(options)
    total_calls = planned_call_count(len(data), options.repeat, scenarios)
    total_evaluations = len(data) * options.repeat * len(scenarios) * len(thresholds)
    print(f"[OK] 모델: {MODEL}")
    print(f"[OK] 메모: {len(data)}개, 반복: {options.repeat}회")
    print(f"[OK] 조건: {len(scenarios)}개, 예상 모델 호출: {total_calls}회")
    print(f"[OK] 임계값: {', '.join(f'{value:.2f}' for value in thresholds)}")
    print(f"[OK] 임계값 평가: {total_evaluations}건 (추가 모델 호출 없음)")
    if options.dry_run:
        print("[DRY-RUN] Ollama를 호출하지 않았고 결과를 저장하지 않았습니다")
        return 0

    output = Path(options.resume).resolve() if options.resume else unique_output_dir()
    if options.resume and not output.is_dir():
        print(f"[FAIL] 결과 폴더가 없습니다: {output}")
        return 2
    output.mkdir(parents=True, exist_ok=True)

    if options.evaluate_only:
        detailed, metrics_rows = finalize(output, scenarios, thresholds, definitions, config)
        print(f"[OK] 모델 재호출 없이 {len(detailed)}건을 재평가했습니다")
        print(f"[OK] 보고서: {output / 'reports' / 'summary.md'}")
        return 0

    client = OllamaClient(config["ollamaBaseUrl"], config["connectTimeoutSeconds"], config["readTimeoutSeconds"])
    try:
        installed = client.models()
    except OllamaError as exc:
        print(f"[FAIL] Ollama 연결 실패 ({exc.error_type}): {exc}")
        return 3
    if not model_installed(MODEL, installed):
        print(f"[FAIL] {MODEL}이 없습니다. 먼저 `ollama pull {MODEL}`을 실행하세요")
        return 4

    prompts = {name: load_prompt(ROOT / "prompts" / filename) for name, filename in PROMPT_FILES.items()}
    data_fingerprint = dataset_fingerprint(data)
    metadata = {
        "model": MODEL, "classificationMode": config["classification"]["mode"],
        "evaluationMode": config["evaluation"]["gold_mode"], "promptVersion": PROMPT_VERSION,
        "datasetFingerprint": data_fingerprint, "datasetCount": len(data),
        "repeat": options.repeat, "scenarios": [asdict(scenario) for scenario in scenarios],
        "thresholds": thresholds, "expectedCallCount": total_calls, "status": "RUNNING",
        "startedAt": datetime.now().astimezone().isoformat(), "completedAt": None,
        "environment": f"{platform.system()} {platform.release()}, Python {platform.python_version()}",
        "modelRuns": {
            scenario.id: model_run_identifier(scenario, data_fingerprint) for scenario in scenarios
        },
    }
    write_json(output / "run-metadata.json", metadata)
    print(f"[OK] 결과 디렉터리: {output}")
    completed_calls = 0
    interrupted = False
    try:
        for scenario_index, scenario in enumerate(scenarios, 1):
            raw_path = output / "raw" / scenario.id / "results.jsonl"
            existing = read_jsonl(raw_path) if raw_path.exists() else []
            completed_keys = {(row["testId"], int(row["repeatNumber"])) for row in existing}
            client.unload(MODEL)
            print(f"\n[{scenario_index}/{len(scenarios)} 조건] {scenario.id}")
            for item_index, item in enumerate(data, 1):
                for repeat_number in range(1, options.repeat + 1):
                    key = (item["testId"], repeat_number)
                    if key in completed_keys:
                        print(f"[SKIP] 원본 응답 존재: {scenario.id} {item['testId']} 반복 {repeat_number}")
                        continue
                    if scenario.structure == "split":
                        category_prompt = build_prompt(
                            prompts["category"], item["input"], categories, item.get("title", ""),
                            definitions, include_category_descriptions=scenario.category_descriptions,
                        )
                        category_call = invoke_multi(
                            client, config, category_prompt, definitions, integrated=False,
                        )
                        organize_call = None
                        integrated_call = None
                    else:
                        category_call = organize_call = None
                        integrated_prompt = build_prompt(
                            prompts["integrated"], item["input"], categories, item.get("title", ""),
                            definitions, include_category_descriptions=scenario.category_descriptions,
                        )
                        integrated_call = invoke_multi(
                            client, config, integrated_prompt, definitions, integrated=True,
                        )
                    record = make_raw_record(
                        scenario, item, repeat_number, category_call, organize_call, integrated_call,
                    )
                    record["modelRunId"] = model_run_identifier(scenario, data_fingerprint)
                    append_jsonl(raw_path, record)
                    completed_calls += record["callCount"]
                    top1 = record["validPredictions"][0]["categoryId"] if record["validPredictions"] else "없음"
                    print(
                        f"[{item_index}/{len(data)}] {item['testId']} 반복 {repeat_number} | "
                        f"Top-1 {top1} | {record['totalDurationMs']:.0f}ms"
                    )
    except KeyboardInterrupt:
        interrupted = True
        print("\n[WARN] 중단 요청을 받았습니다. 저장된 원본 응답까지만 평가합니다")

    detailed, _ = finalize(output, scenarios, thresholds, definitions, config)
    metadata.update({
        "status": "INTERRUPTED" if interrupted else "COMPLETED",
        "completedAt": datetime.now().astimezone().isoformat(),
        "callsCompletedThisRun": completed_calls, "detailedEvaluationCount": len(detailed),
    })
    write_json(output / "run-metadata.json", metadata)
    print(f"[{'PARTIAL' if interrupted else 'OK'}] 보고서: {output / 'reports' / 'summary.md'}")
    return 130 if interrupted else 0


if __name__ == "__main__":
    raise SystemExit(main())
