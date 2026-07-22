from __future__ import annotations

import argparse
import platform
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.auto_evaluator import evaluate
from src.comparison import compare_result_directories
from src.dataset_loader import (
    load_categories,
    load_category_definitions,
    load_dataset,
    load_memo_dataset,
    validate_expected_categories,
)
from src.metrics import classification_metrics, confidence_metrics, nullable_average, nullable_rate, operational_metrics
from src.model_config import (
    ModelConfig,
    ModelConfigError,
    ModelSelection,
    PricingConfig,
    calculate_cost,
    load_models,
    load_pricing,
    load_suites,
    safe_filename,
    select_models,
)
from src.ollama_client import OllamaClient, OllamaError
from src.prompt_builder import build_prompt, load_prompt
from src.providers import ModelRequest, ModelResponse, OllamaProvider, OpenAIProvider, sanitize_error
from src.response_parser import output_schema, parse_response
from src.result_writer import write_csv, write_json
from src.settings import Settings, load_settings


ROOT = Path(__file__).resolve().parent
MODES = ("category-only", "summary-only", "metadata-only", "integrated")
PROMPT_FILES = {
    "category-only": "category-prompt-v1.txt",
    "summary-only": "summary-prompt-v1.txt",
    "metadata-only": "metadata-prompt-v1.txt",
    "integrated": "integrated-prompt-v2.txt",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ollama/OpenAI 공통 AI 텍스트 테스트")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--model", help="config/models.yaml의 내부 모델 ID")
    target.add_argument("--suite", help="config/model-suites.yaml의 Suite 이름")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--list-models", action="store_true")
    action.add_argument("--list-suites", action="store_true")
    action.add_argument("--modes", nargs="+", choices=MODES)
    action.add_argument("--all-modes", action="store_true", help="네 가지 모드 모두 실행")
    for mode in MODES:
        action.add_argument(f"--{mode}", action="store_true")
    parser.add_argument("--test-ids", nargs="+")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--memo-only", action="store_true")
    parser.add_argument("--include-json", action="store_true")
    return parser.parse_args(argv)


def selected_modes(options: argparse.Namespace) -> list[str]:
    if options.modes:
        return list(dict.fromkeys(options.modes))
    if options.all_modes:
        return list(MODES)
    for mode in MODES:
        if getattr(options, mode.replace("-", "_")):
            return [mode]
    return ["integrated"]


def load_project_config() -> dict[str, Any]:
    value = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("config.yaml 형식이 올바르지 않습니다")
    return value


def load_test_data(options: argparse.Namespace) -> tuple[list[dict], list[str], list[dict], str]:
    memo_root = ROOT / "dataset" / "memo"
    categories = load_categories(memo_root)
    definitions = load_category_definitions(ROOT / "config" / "categories.json", memo_root)
    memo_data = load_memo_dataset(memo_root, categories)
    json_data = load_dataset(ROOT / "dataset" / "text-test-data.json") if options.include_json else []
    if json_data:
        validate_expected_categories(json_data, categories)
    data = memo_data if options.memo_only or not json_data else json_data + memo_data
    if options.test_ids:
        known = {item["testId"] for item in data}
        unknown = sorted(set(options.test_ids) - known)
        if unknown:
            raise ValueError(f"존재하지 않는 testId: {', '.join(unknown)}")
        requested = set(options.test_ids)
        data = [item for item in data if item["testId"] in requested]
    if options.limit is not None:
        if options.limit < 1:
            raise ValueError("--limit은 1 이상이어야 합니다")
        data = data[: options.limit]
    if not data:
        raise ValueError("실행할 테스트 데이터가 없습니다")
    return data, categories, definitions, "memo+json" if json_data and not options.memo_only else "memo"


def selection_ids(options: argparse.Namespace, suites: dict[str, tuple[str, ...]]) -> tuple[list[str], str]:
    if options.model:
        return [options.model], options.model
    if options.suite:
        if options.suite not in suites:
            raise ModelConfigError(f"존재하지 않는 suite: {options.suite}")
        return list(suites[options.suite]), options.suite
    return ["qwen-local"], "qwen-local"


def planned_output(modes: list[str], selector: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = f"{modes[0]}-{selector}" if len(modes) == 1 else selector
    base = ROOT / "results" / f"{timestamp}-{safe_filename(suffix)}"
    candidate = base
    index = 1
    while candidate.exists():
        candidate = Path(f"{base}-{index}")
        index += 1
    return candidate


def generate_multi_mode_report(output: Path, modes: list[str]) -> Path:
    mode_directories = [output / mode for mode in modes]
    missing = [str(path) for path in mode_directories if not path.is_dir()]
    if missing:
        raise ValueError(f"종합 보고서에 필요한 모드 폴더가 없습니다: {', '.join(missing)}")
    return compare_result_directories(mode_directories, ROOT / "results", output)


def print_models(models: dict[str, ModelConfig]) -> None:
    print(f"{'ID':<24} {'Provider':<10} {'Model':<20} Enabled")
    for config in models.values():
        print(f"{config.id:<24} {config.provider:<10} {config.model:<20} {str(config.enabled).lower()}")


def print_suites(suites: dict[str, tuple[str, ...]]) -> None:
    print(f"{'Suite':<20} Models")
    for name, model_ids in suites.items():
        print(f"{name:<20} {', '.join(model_ids)}")


def print_dry_run(
    modes: list[str], selections_by_mode: dict[str, list[ModelSelection]], data: list[dict],
    repeat: int, settings: Settings, output: Path, api_key_env: str,
) -> None:
    print("[DRY-RUN] 실제 모델 호출과 결과 파일 생성을 수행하지 않습니다.")
    print(f"테스트 모드: {', '.join(modes)}")
    for mode in modes:
        print(f"\n[{mode}]")
        for selection in selections_by_mode[mode]:
            config = selection.config
            provider = config.provider if config else "N/A"
            model = config.model if config else "N/A"
            suffix = "" if selection.status == "READY" else f" ({selection.status}: {selection.error_type})"
            print(f"- {selection.model_id} | {provider} | {model}{suffix}")
    print(f"데이터 개수: {len(data)}")
    print(f"testId: {', '.join(item['testId'] for item in data)}")
    for mode in modes:
        ready = sum(selection.status == "READY" for selection in selections_by_mode[mode])
        print(f"{mode} 모델당 예상 요청 수: {len(data) * repeat}")
        print(f"{mode} 실행 가능 모델 예상 요청 수: {ready * len(data) * repeat}")
    total = sum(
        sum(selection.status == "READY" for selection in selections_by_mode[mode]) * len(data) * repeat
        for mode in modes
    )
    print(f"전체 예상 요청 수: {total}")
    needs_openai = any(
        selection.config and selection.config.provider == "openai"
        for mode in modes for selection in selections_by_mode[mode]
    )
    print(f"필요한 환경 변수: {api_key_env if needs_openai else '없음'}")
    print(f"{api_key_env}: {'configured' if settings.key_configured(api_key_env) else 'missing'}")
    print(f"결과 저장 예정 경로: {output}")


def _model_available(wanted: str, installed: list[str]) -> bool:
    return wanted in installed or any(name.split(":")[0] == wanted for name in installed)


def make_providers(config: dict[str, Any], settings: Settings) -> dict[str, Any]:
    client = OllamaClient(config["ollamaBaseUrl"], config["connectTimeoutSeconds"], config["readTimeoutSeconds"])
    openai_config = config.get("openai", {})
    api_key_env = openai_config.get("apiKeyEnv", "OPENAI_API_KEY")
    return {
        "ollama": OllamaProvider(client, config["keepAlive"], config.get("seed"), config.get("contextLength"), config.get("thinking")),
        "openai": OpenAIProvider(
            settings.key_for(api_key_env),
            base_url=openai_config.get("baseUrl"),
            api_mode=openai_config.get("apiMode", "responses"),
        ),
    }


def preflight(
    selections: list[ModelSelection], providers: dict[str, Any], settings: Settings, api_key_env: str
) -> list[ModelSelection]:
    installed: list[str] | None = None
    ollama_error: str | None = None
    if any(s.status == "READY" and s.config and s.config.provider == "ollama" for s in selections):
        try:
            installed = providers["ollama"].available_models()
        except OllamaError as exc:
            ollama_error = sanitize_error(exc)
    result: list[ModelSelection] = []
    for selection in selections:
        config = selection.config
        if selection.status != "READY" or config is None:
            result.append(selection)
        elif config.provider == "openai" and not settings.key_configured(api_key_env):
            result.append(ModelSelection(config.id, config, "SKIPPED", "MISSING_API_KEY", f"{api_key_env} is not configured"))
        elif config.provider == "ollama" and ollama_error:
            result.append(ModelSelection(config.id, config, "SKIPPED", "CONNECTION_ERROR", ollama_error))
        elif config.provider == "ollama" and installed is not None and not _model_available(config.model, installed):
            result.append(ModelSelection(config.id, config, "SKIPPED", "MODEL_NOT_FOUND", f"Ollama 모델이 설치되지 않았습니다: {config.model}"))
        else:
            result.append(selection)
    return result


def _provider_failure(response: ModelResponse, info: dict[str, Any]) -> tuple[str | None, str | None]:
    if response.status != "SUCCESS":
        return response.error_type, response.error_message
    if not info.get("rawResponse", "").strip():
        return "EMPTY_RESPONSE", "모델 응답이 비어 있습니다"
    if not info.get("jsonValid"):
        return "JSON_PARSE_ERROR", info.get("validationError") or "JSON 파싱 실패"
    if not info.get("schemaValid"):
        return "SCHEMA_ERROR", info.get("validationError") or "Schema 검증 실패"
    if info.get("extraTextDetected"):
        return "SCHEMA_ERROR", "JSON 외 텍스트가 포함되었습니다"
    if info.get("thinkingTagDetected"):
        return "SCHEMA_ERROR", "<think> 내용이 노출되었습니다"
    return None, None


def _row(record: dict[str, Any]) -> dict[str, Any]:
    response = record["response"]
    parsed = record["parsedResponse"] or {}
    expected = record["expected"]
    evaluation = record["evaluation"]
    provider_meta = response.get("providerMetadata") or {}
    expected_categories = expected.get("categories", [])
    return {
        "testId": record["testId"], "datasetKey": record["datasetKey"], "datasetType": record["datasetType"],
        "testMode": record["testMode"], "title": record.get("title", ""), "sourcePath": record.get("sourcePath", ""),
        "model": record["modelId"], "modelId": record["modelId"], "provider": record["provider"],
        "requestedModel": record["requestedModel"], "resolvedModel": response.get("resolvedModel"),
        "runType": "WARM", "runNumber": record["runNumber"], "promptVersion": record["promptVersion"],
        "expectedCategory": expected_categories[0] if len(expected_categories) == 1 else " | ".join(expected_categories),
        "generatedSummary": parsed.get("summary", ""), "generatedCategory": parsed.get("category", ""),
        "confidence": parsed.get("confidence"), "generatedTags": " | ".join(parsed.get("tags", [])),
        "generatedKeywords": " | ".join(parsed.get("keywords", [])), **evaluation,
        "totalDurationMs": response.get("latencyMs"), "loadDurationMs": provider_meta.get("loadDurationMs"),
        "evalDurationMs": provider_meta.get("generationDurationMs"), "tokensPerSecond": provider_meta.get("tokensPerSecond"),
        "promptEvalCount": response.get("inputTokens"), "evalCount": response.get("outputTokens"),
        "inputTokens": response.get("inputTokens"), "outputTokens": response.get("outputTokens"),
        "totalTokens": response.get("totalTokens"), "cachedInputTokens": response.get("cachedInputTokens"),
        "reasoningTokens": response.get("reasoningTokens"), "estimatedCost": record.get("estimatedCost"),
        "requestFailed": response.get("status") != "SUCCESS", "status": response.get("status"),
        "errorType": response.get("errorType") or "", "errorMessage": response.get("errorMessage") or "",
        "attemptCount": response.get("attemptCount"), "structuredOutputRequested": response.get("structuredOutputRequested"),
        "structuredOutputApplied": response.get("structuredOutputApplied"),
        "structuredOutputFallbackUsed": response.get("structuredOutputFallbackUsed"),
        "structuredOutputFallbackReason": response.get("structuredOutputFallbackReason"),
        "extraTextDetected": evaluation.get("extraTextDetected"), "thinkingTagDetected": evaluation.get("thinkingTagDetected"),
        "executedAt": record["executedAt"],
    }


def run_mode(
    mode: str,
    out: Path,
    selections: list[ModelSelection],
    data: list[dict],
    categories: list[str],
    definitions: list[dict],
    dataset_type: str,
    project_config: dict[str, Any],
    pricing: PricingConfig,
    settings: Settings,
    repeat: int,
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    providers = make_providers(project_config, settings)
    openai_config = project_config.get("openai", {})
    api_key_env = openai_config.get("apiKeyEnv", "OPENAI_API_KEY")
    selections = preflight(selections, providers, settings, api_key_env)
    prompt_version = project_config["promptVersions"][mode]
    prompt_template = load_prompt(ROOT / "prompts" / PROMPT_FILES[mode])
    schema = output_schema(categories, mode)
    started = datetime.now().astimezone()
    metadata: dict[str, Any] = {
        "testMode": mode, "datasetType": dataset_type, "datasetCount": len(data),
        "testIds": [item["testId"] for item in data], "promptVersion": prompt_version,
        "promptFile": PROMPT_FILES[mode], "categories": categories,
        "models": [selection.model_id for selection in selections],
        "modelConfigs": [
            {
                "id": selection.model_id,
                "provider": selection.config.provider if selection.config else None,
                "requestedModel": selection.config.model if selection.config else None,
                "selectionStatus": selection.status,
                "selectionErrorType": selection.error_type,
                "selectionErrorMessage": selection.error_message,
            }
            for selection in selections
        ],
        "startedAt": started.isoformat(), "completedAt": None, "status": "RUNNING",
        "environment": f"{platform.system()} {platform.release()}, Python {platform.python_version()}",
        "environmentVariables": {api_key_env: "configured" if settings.key_configured(api_key_env) else "missing"},
        "options": {
            "temperatureRequested": project_config.get("temperature"), "repeat": repeat,
            "streaming": False, "externalSearch": False, "tools": False,
            "providerDifferences": "GMS OpenAI 호환 Chat Completions에는 temperature/seed/contextLength를 적용하지 않음; 토큰 측정 기준은 provider별로 다를 수 있음",
            "openaiEndpoint": openai_config.get("baseUrl", "default"),
            "openaiApiMode": openai_config.get("apiMode", "responses"),
        },
        "pricing": {"currency": pricing.currency, "unit": pricing.unit, "updatedAt": pricing.updated_at},
    }
    write_json(out / "run-metadata.json", metadata)
    all_records: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    interrupted = False
    try:
        for model_index, selection in enumerate(selections, 1):
            config = selection.config
            print(f"[{model_index}/{len(selections)} 모델] {selection.model_id}")
            model_records: list[dict[str, Any]] = []
            if selection.status != "READY" or config is None:
                skipped = {
                    "modelId": selection.model_id,
                    "provider": config.provider if config else None,
                    "requestedModel": config.model if config else None,
                    "status": "SKIPPED", "errorType": selection.error_type, "errorMessage": selection.error_message,
                    "requests": [],
                }
                write_json(out / "model-results" / f"{safe_filename(selection.model_id)}.json", skipped)
                failures.append({"modelId": selection.model_id, "testId": "N/A", "status": "SKIPPED", "errorType": selection.error_type, "errorMessage": selection.error_message})
                print(f"[SKIPPED] {selection.error_type}: {selection.error_message}")
                continue
            provider = providers[config.provider]
            request_number = 0
            for item in data:
                for run_number in range(1, repeat + 1):
                    request_number += 1
                    print(f"[{request_number}/{len(data) * repeat} 요청] {item['testId']} ({run_number}/{repeat})")
                    built_prompt = build_prompt(prompt_template, item["input"], categories, item.get("title", ""), definitions)
                    request = ModelRequest(built_prompt, schema, mode, item["testId"], project_config.get("temperature"))
                    try:
                        response = provider.generate(request, config)
                    except Exception as exc:
                        response = ModelResponse(
                            provider=config.provider, model_id=config.id, requested_model=config.model,
                            status="FAILED", error_type="UNKNOWN_ERROR", error_message=sanitize_error(exc),
                        )
                    info = parse_response(response.raw_text, categories, mode)
                    response.parsed_output = info.get("parsedResponse")
                    error_type, error_message = _provider_failure(response, info)
                    if error_type:
                        response.status = "FAILED" if response.status != "SKIPPED" else "SKIPPED"
                        response.error_type = error_type
                        response.error_message = sanitize_error(error_message or error_type)
                    evaluation = evaluate(info, item["expected"], categories, mode, item["input"])
                    response_dict = response.to_dict()
                    cost = calculate_cost(pricing, config.id, response.input_tokens, response.output_tokens)
                    record = {
                        "testId": item["testId"], "datasetKey": f"{item.get('datasetType', 'unknown')}:{item['testId']}",
                        "datasetType": item.get("datasetType", ""), "testMode": mode,
                        "title": item.get("title", ""), "sourcePath": item.get("sourcePath", ""),
                        "expected": item["expected"], "modelId": config.id, "provider": config.provider,
                        "requestedModel": config.model, "runNumber": run_number, "promptVersion": prompt_version,
                        "response": response_dict, "rawResponse": response.raw_text,
                        "parsedResponse": info.get("parsedResponse"), "evaluation": evaluation,
                        "estimatedCost": cost, "executedAt": datetime.now().astimezone().isoformat(),
                    }
                    raw_file = out / "raw-responses" / safe_filename(config.id) / f"{safe_filename(item['testId'])}-{run_number}.json"
                    write_json(raw_file, {"testId": item["testId"], **response_dict, "estimatedCost": cost})
                    model_records.append(record)
                    all_records.append(record)
                    row = _row(record)
                    rows.append(row)
                    if response.status != "SUCCESS":
                        failures.append({
                            "modelId": config.id, "testId": item["testId"], "status": response.status,
                            "errorType": response.error_type, "errorMessage": response.error_message,
                        })
                    print(f"[{response.status}] {response.error_type or 'OK'} | {response.latency_ms:.1f}ms")
            model_status = "COMPLETED" if all(r["response"]["status"] == "SUCCESS" for r in model_records) else "COMPLETED_WITH_FAILURES"
            write_json(out / "model-results" / f"{safe_filename(config.id)}.json", {
                "modelId": config.id, "provider": config.provider, "requestedModel": config.model,
                "resolvedModels": sorted({r["response"].get("resolvedModel") for r in model_records if r["response"].get("resolvedModel")}),
                "status": model_status, "requests": model_records,
            })
    except KeyboardInterrupt:
        interrupted = True
        print("\n[WARN] 사용자 중단: 완료된 결과를 저장합니다.")
    metadata["completedAt"] = datetime.now().astimezone().isoformat()
    metadata["status"] = "INTERRUPTED" if interrupted else "COMPLETED"
    metadata["structuredOutput"] = _structured_summary(rows)
    write_json(out / "run-metadata.json", metadata)
    write_json(out / "evaluation-results.json", rows)
    comparison = build_comparison(rows, selections, categories, mode, pricing)
    write_csv(out / "comparison.csv", [
        {key: "N/A" if value is None else value for key, value in item.items()}
        for item in comparison
    ])
    write_csv(out / "failures.csv", failures, ["modelId", "testId", "status", "errorType", "errorMessage"])
    write_confusion_matrices(out, rows, categories, mode)
    write_report(out / "report.md", metadata, comparison, rows, failures)
    if interrupted:
        raise KeyboardInterrupt


def _structured_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_model: dict[str, dict[str, Any]] = {}
    for row in rows:
        entry = by_model.setdefault(row["modelId"], {"requested": True, "appliedCount": 0, "fallbackCount": 0, "reasons": []})
        entry["appliedCount"] += bool(row.get("structuredOutputApplied"))
        entry["fallbackCount"] += bool(row.get("structuredOutputFallbackUsed"))
        reason = row.get("structuredOutputFallbackReason")
        if reason and reason not in entry["reasons"]:
            entry["reasons"].append(reason)
    return by_model


def build_comparison(
    rows: list[dict[str, Any]], selections: list[ModelSelection], categories: list[str], mode: str, pricing: PricingConfig
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for selection in selections:
        config = selection.config
        model_rows = [row for row in rows if row["modelId"] == selection.model_id]
        if selection.status != "READY" or config is None:
            result.append({
                "modelId": selection.model_id, "provider": config.provider if config else "N/A",
                "model": config.model if config else "N/A", "status": "SKIPPED", "callCount": 0,
                "successRate": "N/A", "jsonSuccessRate": "N/A", "schemaSuccessRate": "N/A",
                "categoryAccuracy": "N/A", "macroF1": "N/A", "averageLatencyMs": "N/A", "p95LatencyMs": "N/A",
                "inputTokens": "N/A", "outputTokens": "N/A", "estimatedCost": "N/A",
            })
            continue
        classification = classification_metrics(model_rows, categories) if mode in ("category-only", "integrated") else {}
        confidence = confidence_metrics(model_rows) if mode == "category-only" else {}
        op = operational_metrics(model_rows)
        input_values = [row["inputTokens"] for row in model_rows if row.get("inputTokens") is not None]
        output_values = [row["outputTokens"] for row in model_rows if row.get("outputTokens") is not None]
        costs = [row["estimatedCost"] for row in model_rows if row.get("estimatedCost") is not None]
        result.append({
            "modelId": config.id, "provider": config.provider, "model": config.model,
            "status": "COMPLETED" if all(not row.get("requestFailed") for row in model_rows) else "COMPLETED_WITH_FAILURES",
            "callCount": len(model_rows), "successRate": nullable_rate(model_rows, "responseReceived"),
            "jsonSuccessRate": nullable_rate(model_rows, "jsonValid"), "schemaSuccessRate": nullable_rate(model_rows, "schemaValid"),
            "extraTextRate": nullable_rate(model_rows, "extraTextDetected"), "thinkingExposureRate": nullable_rate(model_rows, "thinkingTagDetected"),
            "categoryAccuracy": classification.get("accuracy"), "macroPrecision": classification.get("macroPrecision"),
            "macroRecall": classification.get("macroRecall"), "macroF1": classification.get("macroF1"),
            "averageConfidence": confidence.get("averageConfidence"),
            "averageConfidenceCorrect": confidence.get("averageConfidenceCorrect"),
            "averageConfidenceIncorrect": confidence.get("averageConfidenceIncorrect"),
            "requiredKeywordRecall": nullable_average(model_rows, "requiredKeywordRecall"),
            "summaryPointRecall": nullable_average(model_rows, "summaryPointRecall"),
            "forbiddenClaimRate": nullable_rate(model_rows, "possibleHallucination"),
            "tagCountValidRate": nullable_rate(model_rows, "tagCountValid"),
            "keywordCountValidRate": nullable_rate(model_rows, "keywordCountValid"),
            "tagDuplicateFreeRate": nullable_rate(model_rows, "tagDuplicateFree"),
            "keywordDuplicateFreeRate": nullable_rate(model_rows, "keywordDuplicateFree"),
            "sourceKeywordRatio": nullable_average(model_rows, "sourceKeywordRatio"),
            "averageLatencyMs": op["averageResponseTimeMs"], "medianLatencyMs": op["medianResponseTimeMs"],
            "p95LatencyMs": op["p95ResponseTimeMs"], "minLatencyMs": op["minResponseTimeMs"], "maxLatencyMs": op["maxResponseTimeMs"],
            "inputTokens": sum(input_values) if input_values else None, "outputTokens": sum(output_values) if output_values else None,
            "estimatedCost": sum(costs) if costs else None,
            "averageCostPerSuccess": sum(costs) / sum(not row.get("requestFailed") for row in model_rows) if costs and any(not row.get("requestFailed") for row in model_rows) else None,
            "currency": pricing.currency,
        })
    return result


def write_confusion_matrices(out: Path, rows: list[dict[str, Any]], categories: list[str], mode: str) -> None:
    if mode not in ("category-only", "integrated"):
        return
    for model_id in sorted({row["modelId"] for row in rows}):
        matrix = classification_metrics([row for row in rows if row["modelId"] == model_id], categories)["confusionMatrix"]
        values = [{"actual": actual, **matrix[actual]} for actual in categories]
        write_csv(out / "confusion-matrices" / f"{safe_filename(model_id)}.csv", values, ["actual", *categories])


def _display(value: Any, percent: bool = False) -> str:
    if value is None or value == "N/A":
        return "N/A"
    if isinstance(value, float):
        return f"{value * 100:.1f}%" if percent else f"{value:.3f}"
    return str(value)


def _markdown_table(headers: list[str], values: list[list[str]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    divider = "|" + "|".join("---" for _ in headers) + "|"
    body = "\n".join("| " + " | ".join(map(str, row)) + " |" for row in values)
    return "\n".join([header, divider, body])


def _best(comparison: list[dict[str, Any]], key: str, reverse: bool) -> str:
    candidates = [row for row in comparison if isinstance(row.get(key), (int, float))]
    if not candidates:
        return "N/A"
    return sorted(candidates, key=lambda row: row[key], reverse=reverse)[0]["modelId"]


def write_report(
    path: Path, metadata: dict[str, Any], comparison: list[dict[str, Any]], rows: list[dict[str, Any]], failures: list[dict[str, Any]]
) -> None:
    table = []
    operations = []
    details = []
    for item in comparison:
        table.append([
            item["modelId"], item["provider"], item["model"], item["callCount"],
            _display(item.get("successRate"), True), _display(item.get("jsonSuccessRate"), True),
            _display(item.get("schemaSuccessRate"), True), _display(item.get("categoryAccuracy"), True),
            _display(item.get("macroF1"), True), _display(item.get("requiredKeywordRecall"), True),
            _display(item.get("summaryPointRecall"), True), _display(item.get("sourceKeywordRatio"), True),
        ])
        operations.append([
            item["modelId"], _display(item.get("averageLatencyMs")), _display(item.get("medianLatencyMs")),
            _display(item.get("p95LatencyMs")), _display(item.get("minLatencyMs")), _display(item.get("maxLatencyMs")),
            _display(item.get("inputTokens")), _display(item.get("outputTokens")),
            _display(item.get("estimatedCost")), _display(item.get("averageCostPerSuccess")),
        ])
        details.append([
            item["modelId"], _display(item.get("extraTextRate"), True), _display(item.get("thinkingExposureRate"), True),
            _display(item.get("macroPrecision"), True), _display(item.get("macroRecall"), True),
            _display(item.get("averageConfidence")), _display(item.get("averageConfidenceCorrect")),
            _display(item.get("averageConfidenceIncorrect")), _display(item.get("forbiddenClaimRate"), True),
            _display(item.get("tagCountValidRate"), True), _display(item.get("keywordCountValidRate"), True),
            _display(item.get("tagDuplicateFreeRate"), True), _display(item.get("keywordDuplicateFreeRate"), True),
        ])
    structured_lines = []
    for model_id, values in metadata.get("structuredOutput", {}).items():
        structured_lines.append(f"- {model_id}: 요청=true, 적용={values['appliedCount']}건, fallback={values['fallbackCount']}건")
    failure_lines = [f"- {item['modelId']} / {item['testId']}: {item['errorType']} - {item['errorMessage']}" for item in failures[:20]] or ["- 없음"]
    accuracy_key = "categoryAccuracy" if metadata["testMode"] in ("category-only", "integrated") else "schemaSuccessRate"
    priced = [item for item in comparison if isinstance(item.get("estimatedCost"), (int, float))]
    cost_candidate = min(priced, key=lambda item: item["estimatedCost"])["modelId"] if priced else "N/A (가격 미설정)"
    report = [
        f"# AI 텍스트 모델 비교 보고서: {metadata['testMode']}", "", "## 실행 정보", "",
        f"- 데이터셋: {metadata['datasetType']}", f"- 데이터 수: {metadata['datasetCount']}",
        f"- testId: {', '.join(metadata['testIds'])}", f"- 프롬프트 버전: {metadata['promptVersion']}",
        f"- 실행 일시: {metadata['startedAt']} ~ {metadata['completedAt']}",
        "- 스트리밍/외부 검색/도구 사용: 모두 비활성화", "- 구조화 출력:", *structured_lines,
        "", "## 형식 안정성 및 모델 성능", "",
        _markdown_table(
            ["Model ID", "Provider", "Model", "호출 수", "성공률", "JSON 성공률", "Schema 성공률", "Category Accuracy", "Macro F1", "필수 키워드", "요약 핵심", "원문 키워드"],
            table,
        ),
        "", "## 세부 품질 지표", "",
        _markdown_table(
            ["Model ID", "JSON 외 텍스트", "think 노출", "Macro Precision", "Macro Recall", "평균 confidence", "정답 confidence", "오답 confidence", "금지 표현", "태그 개수", "키워드 개수", "태그 중복 없음", "키워드 중복 없음"],
            details,
        ),
        "", "## 운영 지표", "",
        _markdown_table(
            ["Model ID", "평균(ms)", "중앙값(ms)", "P95(ms)", "최소(ms)", "최대(ms)", "입력 토큰", "출력 토큰", f"예상 비용({metadata['pricing']['currency']})", "성공 요청당 비용"],
            operations,
        ),
        "", "평가 대상이 아니거나 정답 데이터가 없는 지표는 0이 아니라 N/A로 표시합니다.",
        "", "## 운영 지표 해석", "",
        "- Ollama와 OpenAI가 보고하는 토큰 수의 측정 기준은 서로 다를 수 있습니다.",
        "- 가격이 설정되지 않은 모델의 예상 비용과 성공 요청당 평균 비용은 N/A입니다.",
        "- OpenAI 호출에는 temperature, seed, context length를 억지로 적용하지 않았습니다.",
        "", "## 주요 실패 사례", "", *failure_lines,
        "", "## 주요 혼동 카테고리", "", *_confusion_lines(rows, metadata["categories"]),
        "", "## 카테고리별 분류 지표", "", *_category_detail_lines(rows, metadata["categories"], metadata["testMode"]),
        "", "## 결론", "",
        f"- 가장 정확한 모델: {_best(comparison, accuracy_key, True)}",
        f"- 가장 빠른 모델: {_best(comparison, 'averageLatencyMs', False)}",
        f"- JSON 형식이 가장 안정적인 모델: {_best(comparison, 'schemaSuccessRate', True)}",
        f"- 비용 기준 운영 후보: {cost_candidate}",
        "- 로컬 모델은 외부 API 비용과 네트워크 의존성이 없고, API 모델은 서버 자원 대신 사용량·지연·비용 관리가 필요합니다.",
        "- 현재 결과는 선택한 데이터 수에 한정되므로 작은 --limit 실행만으로 일반화하지 마세요.",
        "- 비용 대비 성능은 정확도, 지연 시간, 토큰, 실제 가격을 함께 보고 판단해야 합니다.",
    ]
    path.write_text("\n".join(report) + "\n", encoding="utf-8")


def _confusion_lines(rows: list[dict[str, Any]], categories: list[str]) -> list[str]:
    lines: list[str] = []
    for model_id in sorted({row["modelId"] for row in rows}):
        metrics = classification_metrics([row for row in rows if row["modelId"] == model_id], categories)
        confusions = metrics.get("majorConfusions", [])
        value = ", ".join(f"{item['actual']} → {item['predicted']} ({item['count']})" for item in confusions[:5]) or "없음"
        lines.append(f"- {model_id}: {value}")
    return lines or ["- N/A"]


def _category_detail_lines(rows: list[dict[str, Any]], categories: list[str], mode: str) -> list[str]:
    if mode not in ("category-only", "integrated"):
        return ["N/A"]
    lines: list[str] = []
    for model_id in sorted({row["modelId"] for row in rows}):
        per_category = classification_metrics([row for row in rows if row["modelId"] == model_id], categories)["perCategory"]
        lines.extend([
            f"### {model_id}", "",
            _markdown_table(
                ["카테고리", "표본", "Precision", "Recall", "F1"],
                [[name, values["support"], _display(values["precision"], True), _display(values["recall"], True), _display(values["f1"], True)] for name, values in per_category.items()],
            ), "",
        ])
    return lines or ["N/A"]


def main(argv: list[str] | None = None) -> int:
    options = parse_args(argv)
    try:
        if options.repeat < 1:
            raise ValueError("--repeat은 1 이상이어야 합니다")
        models = load_models(ROOT / "config" / "models.yaml")
        suites = load_suites(ROOT / "config" / "model-suites.yaml")
        pricing = load_pricing(ROOT / "config" / "model-pricing.yaml")
        project_config = load_project_config()
        if options.list_models:
            print_models(models)
            return 0
        if options.list_suites:
            print_suites(suites)
            return 0
        modes = selected_modes(options)
        ids, selector = selection_ids(options, suites)
        data, categories, definitions, dataset_type = load_test_data(options)
        selections_by_mode = {mode: select_models(models, ids, mode) for mode in modes}
        settings = load_settings(ROOT)
        output = planned_output(modes, selector)
        api_key_env = project_config.get("openai", {}).get("apiKeyEnv", "OPENAI_API_KEY")
        if options.dry_run:
            print_dry_run(modes, selections_by_mode, data, options.repeat, settings, output, api_key_env)
            return 0
        if len(modes) > 1:
            output.mkdir(parents=True)
        for index, mode in enumerate(modes, 1):
            mode_out = output / mode if len(modes) > 1 else output
            print(f"\n[MODE {index}/{len(modes)}] {mode}")
            print(f"[OK] 결과 디렉터리: {mode_out}")
            run_mode(mode, mode_out, selections_by_mode[mode], data, categories, definitions, dataset_type, project_config, pricing, settings, options.repeat)
        if len(modes) > 1:
            report_output = generate_multi_mode_report(output, modes)
            print(f"[OK] 종합 비교 보고서: {report_output / 'comparison-report.md'}")
        print(f"\n[OK] 테스트 완료: {output}")
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, ModelConfigError) as exc:
        print(f"[FAIL] {sanitize_error(exc)}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
