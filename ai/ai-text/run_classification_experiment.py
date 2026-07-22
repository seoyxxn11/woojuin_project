from __future__ import annotations

import argparse
import platform
import statistics
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.auto_evaluator import evaluate
from src.dataset_loader import load_categories, load_category_definitions, load_memo_dataset
from src.metrics import classification_metrics
from src.ollama_client import OllamaClient, OllamaError, performance
from src.prompt_builder import build_prompt, load_prompt
from src.response_parser import output_schema, parse_response
from src.result_writer import append_jsonl, read_jsonl, write_csv, write_json


ROOT = Path(__file__).resolve().parent
MODEL = "qwen3:8b"
RESULTS_ROOT = ROOT / "results" / "3차 분류 구조 비교"


@dataclass(frozen=True)
class Scenario:
    id: str
    structure: str
    category_descriptions: bool
    calls_per_item: int


SCENARIOS = (
    Scenario("split-with-description", "split", True, 2),
    Scenario("split-without-description", "split", False, 2),
    Scenario("integrated-with-description", "integrated", True, 1),
    Scenario("integrated-without-description", "integrated", False, 1),
)
SCENARIO_BY_ID = {scenario.id: scenario for scenario in SCENARIOS}
PROMPT_FILES = {
    "category": "experiment-category-prompt-v1.txt",
    "organize": "experiment-organize-prompt-v1.txt",
    "integrated": "experiment-integrated-prompt-v1.txt",
}
WRONG_ANSWER_FIELDS = (
    "scenario", "structure", "categoryDescriptions", "testId", "repeatNumber",
    "title", "sourcePath", "input", "expectedCategory", "generatedCategory",
    "confidence", "error",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="qwen3:8b 분리/통합 및 카테고리 설명 유무 비교 실험"
    )
    parser.add_argument("--repeat", type=int, default=1, help="메모별 반복 횟수 (기본 1)")
    parser.add_argument("--limit", type=int, help="앞에서부터 실행할 메모 수")
    parser.add_argument("--test-ids", nargs="+", help="실행할 TEXT-001 형식의 ID")
    parser.add_argument(
        "--scenarios",
        nargs="+",
        choices=tuple(SCENARIO_BY_ID),
        help="일부 조건만 실행. 생략하면 네 조건 모두 실행",
    )
    parser.add_argument("--resume", help="중단된 결과 상위 폴더를 지정해 이어서 실행")
    parser.add_argument("--dry-run", action="store_true", help="모델 호출 없이 실행 계획만 확인")
    return parser.parse_args(argv)


def model_installed(wanted: str, installed: list[str]) -> bool:
    return wanted in installed or any(name.split(":")[0] == wanted for name in installed)


def load_experiment_data(options: argparse.Namespace) -> tuple[list[dict], list[str], list[dict]]:
    memo_root = ROOT / "dataset" / "memo"
    folder_categories = load_categories(memo_root)
    definitions = load_category_definitions(ROOT / "config" / "categories.json", memo_root)
    categories = [str(item["name"]) for item in definitions]
    if set(categories) != set(folder_categories):
        raise ValueError("카테고리 정의와 메모 폴더가 일치하지 않습니다")
    data = load_memo_dataset(memo_root, categories)
    if options.test_ids:
        unknown = set(options.test_ids) - {item["testId"] for item in data}
        if unknown:
            raise ValueError(f"없는 testId: {sorted(unknown)}")
        requested = set(options.test_ids)
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


def unique_output_dir() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = RESULTS_ROOT / timestamp
    suffix = 1
    while candidate.exists():
        candidate = RESULTS_ROOT / f"{timestamp}-{suffix}"
        suffix += 1
    return candidate


def response_error(info: dict[str, Any]) -> dict[str, Any]:
    if not str(info.get("rawResponse", "")).strip():
        return {"requestFailed": True, "errorType": "EMPTY_RESPONSE", "errorMessage": "빈 응답"}
    if not info.get("jsonValid"):
        return {"requestFailed": True, "errorType": "INVALID_JSON", "errorMessage": info.get("validationError", "")}
    if not info.get("schemaValid"):
        return {"requestFailed": True, "errorType": "SCHEMA_VALIDATION_FAILED", "errorMessage": info.get("validationError", "")}
    if info.get("extraTextDetected"):
        return {"requestFailed": True, "errorType": "EXTRA_TEXT", "errorMessage": "JSON 외 텍스트 포함"}
    if info.get("thinkingTagDetected"):
        return {"requestFailed": True, "errorType": "THINK_EXPOSED", "errorMessage": "<think> 내용 노출"}
    return {"requestFailed": False, "errorType": "", "errorMessage": ""}


def ollama_metadata(response: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "model", "created_at", "done", "done_reason", "total_duration",
        "load_duration", "prompt_eval_count", "prompt_eval_duration",
        "eval_count", "eval_duration",
    )
    return {key: response.get(key) for key in keys}


def invoke(
    client: OllamaClient,
    config: dict[str, Any],
    prompt: str,
    categories: list[str],
    mode: str,
    expected: dict[str, Any],
    input_text: str,
) -> dict[str, Any]:
    request: dict[str, Any] = {}
    response: dict[str, Any] = {}
    info = parse_response("", categories, mode)
    perf: dict[str, Any] = {}
    error = {"requestFailed": False, "errorType": "", "errorMessage": ""}
    try:
        request, response = client.chat(
            MODEL,
            prompt,
            config["temperature"],
            config["keepAlive"],
            output_schema(categories, mode),
            config.get("seed"),
            config.get("contextLength"),
            config.get("thinking"),
        )
        raw = str(response.get("message", {}).get("content", ""))
        info = parse_response(raw, categories, mode)
        perf = performance(response)
        error = response_error(info)
    except OllamaError as exc:
        error = {"requestFailed": True, "errorType": exc.error_type, "errorMessage": str(exc)}
    return {
        "mode": mode,
        "prompt": prompt,
        "request": request,
        "ollamaResponse": ollama_metadata(response),
        "rawResponse": info["rawResponse"],
        "parsedResponse": info["parsedResponse"],
        "validation": {
            "jsonValid": info["jsonValid"],
            "schemaValid": info["schemaValid"],
            "requiredFieldsPresent": info["requiredFieldsPresent"],
            "extraTextDetected": info["extraTextDetected"],
            "thinkingTagDetected": info["thinkingTagDetected"],
            "validationError": info["validationError"],
        },
        "evaluation": evaluate(info, expected, categories, mode, input_text),
        "performance": perf,
        "error": error,
    }


def sum_call_metric(calls: list[dict[str, Any]], key: str) -> float:
    return sum(float(call.get("performance", {}).get(key, 0) or 0) for call in calls)


def make_record(
    scenario: Scenario,
    item: dict[str, Any],
    repeat_number: int,
    category_call: dict[str, Any] | None,
    organize_call: dict[str, Any] | None,
    integrated_call: dict[str, Any] | None,
) -> dict[str, Any]:
    calls = [integrated_call] if integrated_call is not None else [category_call, organize_call]
    calls = [call for call in calls if call is not None]
    category_source = integrated_call if integrated_call is not None else category_call
    organize_source = integrated_call if integrated_call is not None else organize_call
    if category_source is None or organize_source is None:
        raise ValueError("실험 호출 결과가 누락됐습니다")
    category_parsed = category_source.get("parsedResponse") or {}
    organize_parsed = (organize_source or {}).get("parsedResponse") or {}
    expected_category = item["expected"]["categories"][0]
    generated_category = str(category_parsed.get("category", ""))
    return {
        "testId": item["testId"],
        "title": item.get("title", ""),
        "sourcePath": item.get("sourcePath", ""),
        "input": item["input"],
        "expectedCategory": expected_category,
        "scenario": scenario.id,
        "structure": scenario.structure,
        "categoryDescriptions": scenario.category_descriptions,
        "model": MODEL,
        "repeatNumber": repeat_number,
        "generatedCategory": generated_category,
        "confidence": category_parsed.get("confidence"),
        "generatedSummary": organize_parsed.get("summary", ""),
        "generatedTags": organize_parsed.get("tags", []),
        "generatedKeywords": organize_parsed.get("keywords", []),
        "categoryCorrect": generated_category == expected_category,
        "categorySchemaValid": bool(category_source.get("validation", {}).get("schemaValid")),
        "organizationSchemaValid": bool((organize_source or {}).get("validation", {}).get("schemaValid")),
        "requestFailed": any(call["error"]["requestFailed"] for call in calls),
        "categoryRequestFailed": bool(category_source["error"]["requestFailed"]),
        "organizationRequestFailed": bool((organize_source or {})["error"]["requestFailed"]),
        "callCount": len(calls),
        "totalDurationMs": sum_call_metric(calls, "totalDurationMs"),
        "promptTokenCount": int(sum_call_metric(calls, "promptEvalCount")),
        "outputTokenCount": int(sum_call_metric(calls, "evalCount")),
        "categoryCall": category_call,
        "organizeCall": organize_call,
        "integratedCall": integrated_call,
        "executedAt": datetime.now().astimezone().isoformat(),
    }


def rate(records: list[dict[str, Any]], key: str, inverse: bool = False) -> float | None:
    if not records:
        return None
    values = [not bool(record.get(key)) if inverse else bool(record.get(key)) for record in records]
    return sum(values) / len(values)


def average(records: list[dict[str, Any]], key: str) -> float | None:
    values = [float(record[key]) for record in records if record.get(key) is not None]
    return statistics.mean(values) if values else None


def summarize_scenario(
    scenario: Scenario,
    records: list[dict[str, Any]],
    categories: list[str],
) -> dict[str, Any]:
    classification = classification_metrics(records, categories)
    successful = [record for record in records if not record.get("requestFailed")]
    wrong_answers = wrong_answer_rows(records)
    return {
        "scenario": scenario.id,
        "structure": scenario.structure,
        "categoryDescriptions": scenario.category_descriptions,
        "resultCount": len(records),
        "actualCallCount": sum(int(record.get("callCount", 0)) for record in records),
        "averageCallsPerResult": average(records, "callCount"),
        "pipelineSuccessRate": rate(records, "requestFailed", inverse=True),
        "categorySchemaSuccessRate": rate(records, "categorySchemaValid"),
        "organizationSchemaSuccessRate": rate(records, "organizationSchemaValid"),
        "averageTotalDurationMs": average(successful, "totalDurationMs"),
        "averagePromptTokens": average(successful, "promptTokenCount"),
        "averageOutputTokens": average(successful, "outputTokenCount"),
        "otherSelectionRate": (
            sum(record.get("generatedCategory") == "기타" for record in records) / len(records)
            if records else None
        ),
        "wrongAnswerCount": len(wrong_answers),
        "wrongAnswers": wrong_answers,
        "classification": classification,
    }


def flat_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: record.get(key)
        for key in (
            "testId", "title", "sourcePath", "expectedCategory", "scenario", "structure",
            "categoryDescriptions", "model", "repeatNumber", "generatedCategory", "confidence",
            "generatedSummary", "categoryCorrect", "categorySchemaValid",
            "organizationSchemaValid", "requestFailed", "callCount", "totalDurationMs",
            "promptTokenCount", "outputTokenCount", "executedAt",
        )
    } | {
        "generatedTags": " | ".join(record.get("generatedTags", [])),
        "generatedKeywords": " | ".join(record.get("generatedKeywords", [])),
    }


def wrong_answer_row(record: dict[str, Any]) -> dict[str, Any]:
    category_call = record.get("integratedCall") or record.get("categoryCall") or {}
    error = category_call.get("error") or {}
    validation = category_call.get("validation") or {}
    generated = str(record.get("generatedCategory", "")).strip()
    error_detail = str(error.get("errorType", "")).strip()
    if not error_detail:
        error_detail = str(validation.get("validationError", "")).strip()
    return {
        "scenario": record.get("scenario", ""),
        "structure": record.get("structure", ""),
        "categoryDescriptions": record.get("categoryDescriptions", False),
        "testId": record.get("testId", ""),
        "repeatNumber": record.get("repeatNumber", ""),
        "title": record.get("title", ""),
        "sourcePath": record.get("sourcePath", ""),
        "input": record.get("input", ""),
        "expectedCategory": record.get("expectedCategory", ""),
        "generatedCategory": generated or "응답 없음",
        "confidence": record.get("confidence"),
        "error": error_detail,
    }


def wrong_answer_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [wrong_answer_row(record) for record in records if record.get("categoryCorrect") is not True]


def write_confusion_matrix(path: Path, summary: dict[str, Any], categories: list[str]) -> None:
    matrix = summary["classification"]["confusionMatrix"]
    rows = [
        {"actual": actual, **{predicted: matrix[actual][predicted] for predicted in categories}}
        for actual in categories
    ]
    write_csv(path, rows, ["actual", *categories])


def display(value: float | None, percent: bool = False) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%" if percent else f"{value:.1f}"


def display_delta(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:+.1f}%p"


def markdown_cell(value: Any, limit: int | None = None) -> str:
    text = str(value if value not in (None, "") else "N/A").replace("\r", " ").replace("\n", " ")
    text = text.replace("|", "\\|")
    if limit is not None and len(text) > limit:
        return text[:limit - 1].rstrip() + "…"
    return text


def wrong_answer_table(rows: list[dict[str, Any]], include_scenario: bool) -> list[str]:
    if not rows:
        return ["오답이 없습니다."]
    headers = ["조건"] if include_scenario else []
    headers += ["ID", "반복", "제목", "입력", "정답", "예측", "confidence", "오류"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        values = [markdown_cell(row["scenario"])] if include_scenario else []
        confidence = row.get("confidence")
        values += [
            markdown_cell(row["testId"]),
            markdown_cell(row["repeatNumber"]),
            markdown_cell(row["title"], 30),
            markdown_cell(row["input"], 80),
            markdown_cell(row["expectedCategory"]),
            markdown_cell(row["generatedCategory"]),
            f"{float(confidence):.3f}" if isinstance(confidence, (int, float)) and not isinstance(confidence, bool) else "N/A",
            markdown_cell(row["error"], 40),
        ]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def scenario_report(summary: dict[str, Any]) -> str:
    classification = summary["classification"]
    lines = [
        f"# {summary['scenario']}",
        "",
        f"- 처리 구조: {summary['structure']}",
        f"- 카테고리 설명: {'사용' if summary['categoryDescriptions'] else '미사용'}",
        f"- 결과 수: {summary['resultCount']}",
        f"- 카테고리 정확도: {display(classification['accuracy'], True)}",
        f"- Macro F1: {display(classification['macroF1'], True)}",
        f"- 파이프라인 성공률: {display(summary['pipelineSuccessRate'], True)}",
        f"- 평균 전체 처리 시간: {display(summary['averageTotalDurationMs'])}ms",
        f"- 평균 호출 수: {display(summary['averageCallsPerResult'])}",
        f"- 기타 선택률: {display(summary['otherSelectionRate'], True)}",
        "",
        f"## 오답 데이터 ({summary['wrongAnswerCount']}건)",
        "",
        *wrong_answer_table(summary["wrongAnswers"], include_scenario=False),
        "",
    ]
    return "\n".join(lines)


def delta(first: dict[str, Any], second: dict[str, Any]) -> float | None:
    a = first["classification"]["accuracy"]
    b = second["classification"]["accuracy"]
    return a - b if a is not None and b is not None else None


def write_comparison(output: Path, summaries: list[dict[str, Any]]) -> None:
    by_id = {summary["scenario"]: summary for summary in summaries}
    deltas: dict[str, float | None] = {}
    pairs = {
        "descriptionEffectSplit": ("split-with-description", "split-without-description"),
        "descriptionEffectIntegrated": ("integrated-with-description", "integrated-without-description"),
        "splitVsIntegratedWithDescription": ("split-with-description", "integrated-with-description"),
        "splitVsIntegratedWithoutDescription": ("split-without-description", "integrated-without-description"),
    }
    for name, (first, second) in pairs.items():
        deltas[name] = delta(by_id[first], by_id[second]) if first in by_id and second in by_id else None
    wrong_answers = [row for summary in summaries for row in summary["wrongAnswers"]]
    write_json(output / "comparison-summary.json", {
        "model": MODEL,
        "scenarios": summaries,
        "accuracyDeltas": deltas,
        "wrongAnswerCount": len(wrong_answers),
        "wrongAnswers": wrong_answers,
    })
    write_json(output / "wrong-answers.json", wrong_answers)
    write_csv(output / "wrong-answers.csv", wrong_answers, list(WRONG_ANSWER_FIELDS))
    lines = [
        "# qwen3:8b 분류 구조 비교",
        "",
        "| 조건 | 구조 | 설명 | 정확도 | Macro F1 | 성공률 | 평균 시간(ms) | 평균 호출 수 | 기타 선택률 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in summaries:
        classification = summary["classification"]
        lines.append(
            f"| {summary['scenario']} | {summary['structure']} | "
            f"{'있음' if summary['categoryDescriptions'] else '없음'} | "
            f"{display(classification['accuracy'], True)} | {display(classification['macroF1'], True)} | "
            f"{display(summary['pipelineSuccessRate'], True)} | {display(summary['averageTotalDurationMs'])} | "
            f"{display(summary['averageCallsPerResult'])} | {display(summary['otherSelectionRate'], True)} |"
        )
    lines += [
        "",
        "## 정확도 차이",
        "",
        f"- 분리 방식의 설명 효과: {display_delta(deltas['descriptionEffectSplit'])}",
        f"- 통합 방식의 설명 효과: {display_delta(deltas['descriptionEffectIntegrated'])}",
        f"- 설명이 있을 때 분리-통합 차이: {display_delta(deltas['splitVsIntegratedWithDescription'])}",
        f"- 설명이 없을 때 분리-통합 차이: {display_delta(deltas['splitVsIntegratedWithoutDescription'])}",
        "",
        "> 양수는 앞에 적힌 조건의 정확도가 더 높다는 의미입니다.",
        "",
        f"## 전체 오답 데이터 ({len(wrong_answers)}건)",
        "",
        *wrong_answer_table(wrong_answers, include_scenario=True),
        "",
    ]
    (output / "comparison-report.md").write_text("\n".join(lines), encoding="utf-8")


def finalize(output: Path, scenarios: list[Scenario], categories: list[str]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for scenario in scenarios:
        scenario_dir = output / scenario.id
        raw_path = scenario_dir / "raw" / "results.jsonl"
        records = read_jsonl(raw_path) if raw_path.exists() else []
        summary = summarize_scenario(scenario, records, categories)
        summaries.append(summary)
        write_json(scenario_dir / "evaluation-results.json", [flat_record(record) for record in records])
        write_csv(scenario_dir / "evaluation-results.csv", [flat_record(record) for record in records])
        write_json(scenario_dir / "metrics.json", summary)
        write_json(scenario_dir / "wrong-answers.json", summary["wrongAnswers"])
        write_csv(
            scenario_dir / "wrong-answers.csv",
            summary["wrongAnswers"],
            list(WRONG_ANSWER_FIELDS),
        )
        write_confusion_matrix(scenario_dir / "confusion-matrix.csv", summary, categories)
        (scenario_dir / "report.md").write_text(scenario_report(summary), encoding="utf-8")
    write_comparison(output, summaries)
    return summaries


def main(argv: list[str] | None = None) -> int:
    options = parse_args(argv)
    if options.repeat < 1:
        print("[FAIL] --repeat는 1 이상이어야 합니다")
        return 2
    if sys.version_info < (3, 11):
        print("[FAIL] Python 3.11 이상이 필요합니다")
        return 2
    try:
        data, categories, definitions = load_experiment_data(options)
    except (OSError, ValueError) as exc:
        print(f"[FAIL] 테스트 데이터 검증 실패: {exc}")
        return 2
    scenarios = selected_scenarios(options)
    total_calls = planned_call_count(len(data), options.repeat, scenarios)
    print(f"[OK] 모델: {MODEL}")
    print(f"[OK] 메모: {len(data)}개, 반복: {options.repeat}회")
    print(f"[OK] 조건: {len(scenarios)}개, 예상 호출: {total_calls}회")
    for scenario in scenarios:
        print(f"- {scenario.id}: 메모당 {scenario.calls_per_item}회 호출")
    if options.dry_run:
        print("[DRY-RUN] Ollama를 호출하지 않았습니다")
        return 0

    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    client = OllamaClient(config["ollamaBaseUrl"], config["connectTimeoutSeconds"], config["readTimeoutSeconds"])
    try:
        installed = client.models()
    except OllamaError as exc:
        print(f"[FAIL] Ollama 연결 실패 ({exc.error_type}): {exc}")
        return 3
    if not model_installed(MODEL, installed):
        print(f"[FAIL] {MODEL}이 없습니다. 먼저 `ollama pull {MODEL}`을 실행하세요")
        return 4

    output = Path(options.resume).resolve() if options.resume else unique_output_dir()
    if options.resume and not output.is_dir():
        print(f"[FAIL] 이어서 실행할 폴더가 없습니다: {output}")
        return 2
    output.mkdir(parents=True, exist_ok=True)
    prompts = {name: load_prompt(ROOT / "prompts" / filename) for name, filename in PROMPT_FILES.items()}
    metadata = {
        "model": MODEL,
        "datasetCount": len(data),
        "repeat": options.repeat,
        "scenarios": [asdict(scenario) for scenario in scenarios],
        "expectedCallCount": total_calls,
        "temperature": config["temperature"],
        "seed": config.get("seed"),
        "thinking": config.get("thinking"),
        "contextLength": config.get("contextLength"),
        "status": "RUNNING",
        "startedAt": datetime.now().astimezone().isoformat(),
        "completedAt": None,
        "environment": f"{platform.system()} {platform.release()}, Python {platform.python_version()}",
    }
    write_json(output / "run-metadata.json", metadata)
    print(f"[OK] 결과 디렉터리: {output}")

    interrupted = False
    completed_calls = 0
    try:
        for scenario_index, scenario in enumerate(scenarios, 1):
            scenario_dir = output / scenario.id
            raw_path = scenario_dir / "raw" / "results.jsonl"
            existing = read_jsonl(raw_path) if raw_path.exists() else []
            completed_keys = {(row["testId"], int(row["repeatNumber"])) for row in existing}
            client.unload(MODEL)
            print(f"\n[{scenario_index}/{len(scenarios)} 조건] {scenario.id}")
            for item_index, item in enumerate(data, 1):
                for repeat_number in range(1, options.repeat + 1):
                    if (item["testId"], repeat_number) in completed_keys:
                        print(f"[SKIP] {scenario.id} {item['testId']} 반복 {repeat_number}")
                        continue
                    include_descriptions = scenario.category_descriptions
                    category_call: dict[str, Any] | None
                    organize_call: dict[str, Any] | None = None
                    integrated_call: dict[str, Any] | None = None
                    if scenario.structure == "split":
                        category_prompt = build_prompt(
                            prompts["category"], item["input"], categories, item.get("title", ""),
                            definitions, include_category_descriptions=include_descriptions,
                        )
                        category_call = invoke(
                            client, config, category_prompt, categories, "category-only",
                            item["expected"], item["input"],
                        )
                        organize_prompt = build_prompt(
                            prompts["organize"], item["input"], categories, item.get("title", "")
                        )
                        organize_call = invoke(
                            client, config, organize_prompt, categories, "organize-only",
                            item["expected"], item["input"],
                        )
                    else:
                        category_call = None
                        integrated_prompt = build_prompt(
                            prompts["integrated"], item["input"], categories, item.get("title", ""),
                            definitions, include_category_descriptions=include_descriptions,
                        )
                        integrated_call = invoke(
                            client, config, integrated_prompt, categories, "integrated",
                            item["expected"], item["input"],
                        )
                    record = make_record(
                        scenario, item, repeat_number, category_call, organize_call, integrated_call
                    )
                    append_jsonl(raw_path, record)
                    completed_calls += record["callCount"]
                    result = "정답" if record["categoryCorrect"] else "오답"
                    print(
                        f"[{item_index}/{len(data)}] {item['testId']} 반복 {repeat_number} | "
                        f"{result} | {record['totalDurationMs']:.0f}ms"
                    )
    except KeyboardInterrupt:
        interrupted = True
        print("\n[WARN] 중단 요청을 받았습니다. 완료된 결과로 보고서를 생성합니다")

    summaries = finalize(output, scenarios, categories)
    metadata["status"] = "INTERRUPTED" if interrupted else "COMPLETED"
    metadata["completedAt"] = datetime.now().astimezone().isoformat()
    metadata["callsCompletedThisRun"] = completed_calls
    metadata["resultCount"] = sum(summary["resultCount"] for summary in summaries)
    write_json(output / "run-metadata.json", metadata)
    print(f"[{'PARTIAL' if interrupted else 'OK'}] 비교 보고서: {output / 'comparison-report.md'}")
    return 130 if interrupted else 0


if __name__ == "__main__":
    raise SystemExit(main())
