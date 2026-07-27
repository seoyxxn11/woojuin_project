from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from run_classification_experiment import evaluate_raw_record
from src.auto_evaluator import evaluate
from src.comparison import compare_result_directories
from src.dataset_loader import (
    load_categories,
    load_category_definitions,
    load_dataset,
    load_memo_dataset,
    load_typed_test_dataset,
    validate_expected_categories,
)
from src.metrics import classification_metrics, confidence_metrics, nullable_average, nullable_rate, operational_metrics
from src.multi_label_selector import category_maps
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
from src.response_parser import (
    output_multi_label_schema,
    output_schema,
    parse_multi_label_response,
    parse_response,
)
from src.result_writer import write_csv, write_json
from src.settings import Settings, load_settings
from src.url_summary_policy import usable_url_summary


ROOT = Path(__file__).resolve().parent
MODES = ("category-only", "summary-only", "metadata-only", "integrated")
PROMPT_FILES = {
    "category-only": "experiment-category-prompt-v1.txt",
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
    parser.add_argument(
        "--category-definitions",
        type=Path,
        help="분류에 사용할 카테고리 설명 JSON (기본: config/categories.json)",
    )
    parser.add_argument(
        "--write-url-summary",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="summary-only/integrated 성공 시 dataset/test URL JSON의 summary 갱신",
    )
    parser.add_argument(
        "--input-type", "--input-types",
        nargs="+", choices=("memo", "url", "image", "all"), default=["all"],
        help="dataset/test에서 실행할 입력 유형 (기본: all)",
    )
    parser.add_argument(
        "--category-descriptions",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="프롬프트에 카테고리 설명과 예시 포함 (기본: 활성화)",
    )
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
    definitions_path = (
        options.category_definitions.resolve()
        if options.category_definitions
        else ROOT / "config" / "categories.json"
    )
    if options.memo_only or options.include_json:
        memo_root = ROOT / "dataset" / "memo"
        categories = load_categories(memo_root)
        definitions = load_category_definitions(definitions_path, memo_root)
        memo_data = load_memo_dataset(memo_root, categories)
        json_data = load_dataset(ROOT / "dataset" / "text-test-data.json") if options.include_json else []
        if json_data:
            validate_expected_categories(json_data, categories)
        data = memo_data if not json_data else json_data + memo_data
        dataset_type = "memo+json" if json_data else "memo"
    else:
        test_root = ROOT / "dataset" / "test"
        data, categories = load_typed_test_dataset(test_root, options.input_type)
        definitions = load_category_definitions(definitions_path, test_root)
        selected_types = sorted({item["inputType"] for item in data})
        dataset_type = "test:" + "+".join(selected_types)
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
    return data, categories, definitions, dataset_type


def selection_ids(options: argparse.Namespace, suites: dict[str, tuple[str, ...]]) -> tuple[list[str], str]:
    if options.model:
        return [options.model], options.model
    if options.suite:
        if options.suite not in suites:
            raise ModelConfigError(f"존재하지 않는 suite: {options.suite}")
        return list(suites[options.suite]), options.suite
    return ["qwen-local"], "qwen-local"


def write_url_summary(item: dict[str, Any], summary: str) -> Path | None:
    """AI가 생성한 URL 요약을 해당 로컬 테스트 JSON에 기록한다."""
    if item.get("inputType") != "url" or not summary.strip():
        return None
    test_root = (ROOT / "dataset" / "test").resolve()
    source = (test_root / str(item.get("sourcePath", ""))).resolve()
    if not source.is_relative_to(test_root) or not source.is_file():
        raise ValueError(f"URL 요약을 기록할 테스트 파일이 없습니다: {source}")
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or str(value.get("type", "")).upper() != "URL":
        raise ValueError(f"URL 테스트 JSON 형식이 아닙니다: {source}")
    value["summary"] = usable_url_summary(summary)
    source.write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return source


def model_input_for_mode(item: dict[str, Any], mode: str) -> str:
    """URL 카테고리 분류에는 원문 content 대신 저장된 summary를 사용한다."""
    original = str(item.get("input", ""))
    if mode != "category-only" or item.get("inputType") != "url":
        return original
    try:
        value = json.loads(original)
    except json.JSONDecodeError:
        return original
    if not isinstance(value, dict):
        return original
    classification_input = {
        "type": "URL",
        "url": value.get("url"),
        "summary": usable_url_summary(value.get("summary")),
    }
    return json.dumps(
        classification_input,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def category_classification_eligible(item: dict[str, Any]) -> bool:
    if item.get("inputType") != "url":
        return True
    try:
        value = json.loads(str(item.get("input", "")))
    except json.JSONDecodeError:
        return False
    return isinstance(value, dict) and bool(usable_url_summary(value.get("summary")))


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
    multi_label = "serviceSelectedCategoryNames" in evaluation
    generated_category = (
        " | ".join(evaluation.get("serviceSelectedCategoryNames", []))
        if multi_label else parsed.get("category", "")
    )
    confidence = (
        evaluation.get("validPredictions", [{}])[0].get("score")
        if multi_label and evaluation.get("validPredictions")
        else parsed.get("confidence")
    )
    row = {
        "testId": record["testId"], "datasetKey": record["datasetKey"], "datasetType": record["datasetType"],
        "testMode": record["testMode"], "title": record.get("title", ""), "sourcePath": record.get("sourcePath", ""),
        "model": record["modelId"], "modelId": record["modelId"], "provider": record["provider"],
        "requestedModel": record["requestedModel"], "resolvedModel": response.get("resolvedModel"),
        "runType": "WARM", "runNumber": record["runNumber"], "promptVersion": record["promptVersion"],
        "expectedCategory": expected_categories[0] if len(expected_categories) == 1 else " | ".join(expected_categories),
        "generatedSummary": parsed.get("summary", ""), "generatedCategory": generated_category,
        "confidence": confidence, "generatedTags": " | ".join(parsed.get("tags", [])),
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
    if multi_label:
        row["categoryCorrect"] = evaluation.get("serviceRelaxedCorrect")
    return row


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
    write_url_summaries: bool = True,
) -> None:
    if mode == "category-only":
        before = len(data)
        data = [item for item in data if category_classification_eligible(item)]
        excluded = before - len(data)
        if excluded:
            print(f"[INFO] 사용 가능한 URL summary가 없어 category-only에서 제외: {excluded}건")
        if not data:
            raise ValueError("category-only에 사용할 수 있는 데이터가 없습니다.")
    out.mkdir(parents=True, exist_ok=True)
    providers = make_providers(project_config, settings)
    openai_config = project_config.get("openai", {})
    api_key_env = openai_config.get("apiKeyEnv", "OPENAI_API_KEY")
    selections = preflight(selections, providers, settings, api_key_env)
    prompt_version = project_config["promptVersions"][mode]
    prompt_template = load_prompt(ROOT / "prompts" / PROMPT_FILES[mode])
    schema = (
        output_multi_label_schema(definitions, integrated=False)
        if mode == "category-only"
        else output_schema(categories, mode)
    )
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
            "categoryDescriptions": project_config.get("includeCategoryDescriptions", True),
            "classificationMode": project_config.get("classification", {}).get("mode"),
            "threshold": project_config.get("classification", {}).get("threshold"),
            "serviceMaxCategories": project_config.get("classification", {}).get("service_max_categories"),
            "ensureAtLeastOne": project_config.get("classification", {}).get("ensure_at_least_one"),
            "writeUrlSummary": write_url_summaries,
            "streaming": False, "externalSearch": False, "tools": False,
            "providerDifferences": "GMS OpenAI 호환 Chat Completions에는 temperature/seed/contextLength를 적용하지 않음; 토큰 측정 기준은 provider별로 다를 수 있음",
            "openaiEndpoint": openai_config.get("baseUrl", "default"),
            "openaiApiMode": openai_config.get("apiMode", "responses"),
        },
        "pricing": {"currency": pricing.currency, "unit": pricing.unit, "updatedAt": pricing.updated_at},
    }
    write_json(out / "run-metadata.json", metadata)
    write_json(out / "category-descriptions.json", definitions)
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
                    model_input = model_input_for_mode(item, mode)
                    built_prompt = build_prompt(
                        prompt_template,
                        model_input,
                        categories,
                        item.get("title", ""),
                        definitions,
                        include_category_descriptions=project_config.get(
                            "includeCategoryDescriptions", True
                        ),
                    )
                    request = ModelRequest(built_prompt, schema, mode, item["testId"], project_config.get("temperature"))
                    try:
                        response = provider.generate(request, config)
                    except Exception as exc:
                        response = ModelResponse(
                            provider=config.provider, model_id=config.id, requested_model=config.model,
                            status="FAILED", error_type="UNKNOWN_ERROR", error_message=sanitize_error(exc),
                        )
                    info = (
                        parse_multi_label_response(response.raw_text, definitions, integrated=False)
                        if mode == "category-only"
                        else parse_response(response.raw_text, categories, mode)
                    )
                    response.parsed_output = info.get("parsedResponse")
                    error_type, error_message = _provider_failure(response, info)
                    if error_type:
                        response.status = "FAILED" if response.status != "SKIPPED" else "SKIPPED"
                        response.error_type = error_type
                        response.error_message = sanitize_error(error_message or error_type)
                    parsed_output = info.get("parsedResponse") or {}
                    generated_summary = parsed_output.get("summary")
                    if (
                        write_url_summaries
                        and mode in {"summary-only", "integrated"}
                        and response.status == "SUCCESS"
                        and info.get("schemaValid") is True
                        and isinstance(generated_summary, str)
                    ):
                        write_url_summary(item, generated_summary)
                    if mode == "category-only":
                        raw_record = {
                            "testId": item["testId"],
                            "title": item.get("title", ""),
                            "sourcePath": item.get("sourcePath", ""),
                            "input": model_input,
                            "expectedCategoryName": item["expected"]["categories"][0],
                            "scenario": "typed-category-classification",
                            "structure": "split",
                            "categoryDescriptions": project_config.get("includeCategoryDescriptions", True),
                            "repeatNumber": run_number,
                            "model": config.id,
                            "rawPredictions": info.get("rawPredictions", []),
                            "validPredictions": info.get("validPredictions", []),
                            "invalidPredictions": info.get("invalidPredictions", []),
                            "categoryParseSuccess": info.get("categoryParseSuccess"),
                            "summaryParseSuccess": None,
                            "organizationParseSuccess": None,
                            "requestFailed": response.status != "SUCCESS",
                            "totalDurationMs": response.latency_ms,
                        }
                        evaluation = evaluate_raw_record(
                            raw_record,
                            float(project_config["classification"]["threshold"]),
                            definitions,
                            project_config["classification"],
                            project_config["evaluation"],
                        )
                        by_id, _ = category_maps(definitions)
                        evaluation["thresholdSelectedCategoryNames"] = [
                            by_id[category_id]["name"]
                            for category_id in evaluation["thresholdSelectedCategoryIds"]
                        ]
                        evaluation["serviceSelectedCategoryNames"] = [
                            by_id[category_id]["name"]
                            for category_id in evaluation["serviceSelectedCategoryIds"]
                        ]
                        evaluation["top1CategoryName"] = (
                            by_id[evaluation["top1CategoryId"]]["name"]
                            if evaluation.get("top1CategoryId") in by_id else ""
                        )
                    else:
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
    write_csv(out / "failures.csv", failures, ["modelId", "testId", "status", "errorType", "errorMessage"])
    write_confusion_matrices(out, rows, categories, mode)
    executed_model_ids = {str(row.get("modelId")) for row in rows if row.get("modelId")}
    if mode == "category-only" and len(executed_model_ids) <= 1:
        write_classification_outputs(out, metadata, rows, categories, definitions)
    else:
        comparison = build_comparison(rows, selections, categories, mode, pricing)
        write_csv(out / "comparison.csv", [
            {key: "N/A" if value is None else value for key, value in item.items()}
            for item in comparison
        ])
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


def _input_type(row: dict[str, Any]) -> str:
    dataset_type = str(row.get("datasetType", "")).lower()
    if dataset_type.startswith("test-"):
        return dataset_type.removeprefix("test-")
    test_id = str(row.get("testId", ""))
    prefix = test_id.partition("-")[0].lower()
    return prefix if prefix in {"memo", "url", "image"} else dataset_type or "unknown"


def _markdown_cell(value: Any) -> str:
    return str(value if value is not None else "").replace("|", r"\|").replace("\r", " ").replace("\n", " ")


def _service_classification_metrics(
    rows: list[dict[str, Any]], definitions: list[dict[str, Any]]
) -> dict[str, Any] | None:
    if not rows:
        return None
    category_names = [str(item["name"]) for item in definitions]
    per_category: dict[str, dict[str, Any]] = {}
    for category in category_names:
        tp = fp = fn = support = 0
        for row in rows:
            gold = str(row.get("expectedCategory", ""))
            predicted = set(row.get("serviceSelectedCategoryNames", []))
            support += gold == category
            tp += gold == category and category in predicted
            fp += gold != category and category in predicted
            fn += gold == category and category not in predicted
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall
            else (0.0 if precision is not None and recall is not None else None)
        )
        per_category[category] = {
            "support": support, "precision": precision, "recall": recall, "f1": f1,
        }
    average = lambda key: (
        sum(float(item[key]) for item in per_category.values() if item[key] is not None)
        / sum(item[key] is not None for item in per_category.values())
        if any(item[key] is not None for item in per_category.values()) else None
    )
    count = len(rows)
    return {
        "count": count,
        "top1Accuracy": sum(bool(row.get("top1Correct")) for row in rows) / count,
        "exactAccuracy": sum(bool(row.get("serviceExactCorrect")) for row in rows) / count,
        "relaxedAccuracy": sum(bool(row.get("serviceRelaxedCorrect")) for row in rows) / count,
        "averageSelectedCategoryCount": (
            sum(len(row.get("serviceSelectedCategoryIds", [])) for row in rows) / count
        ),
        "macroPrecision": average("precision"),
        "macroRecall": average("recall"),
        "macroF1": average("f1"),
        "perCategory": per_category,
    }


def write_classification_outputs(
    out: Path,
    metadata: dict[str, Any],
    rows: list[dict[str, Any]],
    categories: list[str],
    definitions: list[dict[str, Any]],
) -> None:
    """확정된 단일 모델의 카테고리 분류 결과만 입력 유형별로 저장한다."""
    model_ids = sorted({str(row.get("modelId", "")) for row in rows if row.get("modelId")})
    if len(model_ids) > 1:
        raise ValueError("category-only 보고서는 확정 모델 하나만 지원합니다")

    enriched = [{**row, "inputType": _input_type(row)} for row in rows]
    fields = [
        "inputType", "testId", "title", "sourcePath", "expectedCategory",
        "top1CategoryName", "top1Correct",
        "thresholdSelectedCategoryNames", "serviceSelectedCategoryNames",
        "serviceExactCorrect", "serviceRelaxedCorrect",
        "threshold", "fallbackUsed", "serviceLimitApplied", "status",
        "errorType", "errorMessage",
    ]
    write_csv(out / "classification-results.csv", enriched, fields)
    write_json(out / "classification-results.json", enriched)

    sections: list[tuple[str, list[dict[str, Any]]]] = [("전체", enriched)]
    for input_type in ("memo", "url", "image"):
        selected = [row for row in enriched if row["inputType"] == input_type]
        sections.append((input_type, selected))
        write_json(out / "by-input-type" / f"{input_type}.json", selected)
        write_csv(out / "by-input-type" / f"{input_type}.csv", selected, fields)

    summary_rows: list[dict[str, Any]] = []
    report: list[str] = [
        "# 카테고리 분류 테스트 보고서", "",
        "## 실행 정보", "",
        f"- 모델: {model_ids[0] if model_ids else 'N/A'}",
        f"- 데이터셋: {metadata.get('datasetType', '')}",
        f"- 전체 데이터: {len(enriched)}건",
        f"- 카테고리 설명: {'포함' if metadata.get('options', {}).get('categoryDescriptions') else '미포함'}",
        f"- 선택 정책: score {metadata.get('options', {}).get('threshold', 0.65)} 이상, 최대 {metadata.get('options', {}).get('serviceMaxCategories', 2)}개",
        f"- 실행 일시: {metadata.get('startedAt')} ~ {metadata.get('completedAt')}", "",
        "## 정확도 요약", "",
    ]

    overview: list[list[str]] = []
    section_metrics: dict[str, dict[str, Any] | None] = {}
    for label, selected in sections:
        if not selected:
            section_metrics[label] = None
            overview.append([label, "0", "0", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"])
            summary_rows.append({
                "inputType": label, "count": 0, "correctCount": 0,
                "top1Accuracy": None, "exactAccuracy": None, "relaxedAccuracy": None,
                "averageSelectedCategoryCount": None,
                "macroPrecision": None, "macroRecall": None, "macroF1": None,
            })
            continue
        metrics = _service_classification_metrics(selected, definitions)
        assert metrics is not None
        section_metrics[label] = metrics
        correct = sum(row.get("serviceRelaxedCorrect") is True for row in selected)
        overview.append([
            label, str(len(selected)), str(correct), _display(metrics["top1Accuracy"], True),
            _display(metrics["exactAccuracy"], True), _display(metrics["relaxedAccuracy"], True),
            _display(metrics["averageSelectedCategoryCount"]),
            _display(metrics["macroPrecision"], True), _display(metrics["macroRecall"], True),
            _display(metrics["macroF1"], True),
        ])
        summary_rows.append({
            "inputType": label, "count": len(selected), "correctCount": correct,
            "top1Accuracy": metrics["top1Accuracy"], "exactAccuracy": metrics["exactAccuracy"],
            "relaxedAccuracy": metrics["relaxedAccuracy"],
            "averageSelectedCategoryCount": metrics["averageSelectedCategoryCount"],
            "macroPrecision": metrics["macroPrecision"],
            "macroRecall": metrics["macroRecall"], "macroF1": metrics["macroF1"],
        })
    write_json(out / "classification-summary.json", summary_rows)
    write_csv(
        out / "classification-summary.csv", summary_rows,
        [
            "inputType", "count", "correctCount", "top1Accuracy", "exactAccuracy",
            "relaxedAccuracy", "averageSelectedCategoryCount",
            "macroPrecision", "macroRecall", "macroF1",
        ],
    )
    report.append(_markdown_table(
        [
            "구분", "데이터 수", "정답 포함 수", "Top-1", "정확 일치",
            "완화 정확도", "평균 선택 수", "Macro Precision", "Macro Recall", "Macro F1",
        ],
        overview,
    ))

    for label, selected in sections:
        report.extend(["", f"## {label} 결과", ""])
        metrics = section_metrics[label]
        if metrics is None:
            report.append("- 테스트 데이터 없음")
            continue
        category_rows = []
        for category, values in metrics["perCategory"].items():
            category_rows.append([
                category, str(values["support"]), _display(values["precision"], True),
                _display(values["recall"], True), _display(values["f1"], True),
            ])
        report.extend([
            "### 카테고리별 지표", "",
            _markdown_table(["카테고리", "표본", "Precision", "Recall", "F1"], category_rows),
            "", "### 개별 테스트 결과", "",
            _markdown_table(
                ["ID", "정답", "Top-1", "최종 선택", "정답 포함", "점수", "제목"],
                [[
                    _markdown_cell(row.get("testId")), _markdown_cell(row.get("expectedCategory")),
                    _markdown_cell(row.get("top1CategoryName")),
                    _markdown_cell(" / ".join(row.get("serviceSelectedCategoryNames", []))),
                    "O" if row.get("serviceRelaxedCorrect") is True else "X",
                    _markdown_cell(" / ".join(
                        f"{item['categoryName']} {float(item['score']):.2f}"
                        for item in row.get("validPredictions", [])
                    )),
                    _markdown_cell(row.get("title")),
                ] for row in selected],
            ),
        ])

    report.extend(["", "## 카테고리 설명", ""])
    report.append(_markdown_table(
        ["ID", "카테고리", "설명", "예시"],
        [[
            _markdown_cell(item.get("id")), _markdown_cell(item.get("name")),
            _markdown_cell(item.get("description")), _markdown_cell(", ".join(item.get("examples", []))),
        ] for item in definitions],
    ))
    (out / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


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
        project_config["includeCategoryDescriptions"] = options.category_descriptions
        if options.list_models:
            print_models(models)
            return 0
        if options.list_suites:
            print_suites(suites)
            return 0
        modes = selected_modes(options)
        ids, selector = selection_ids(options, suites)
        data, categories, definitions, dataset_type = load_test_data(options)
        print(
            f"[OK] 입력 유형: {', '.join(sorted({item.get('inputType', item.get('datasetType', 'unknown')) for item in data}))}"
        )
        print(
            f"[OK] 카테고리 설명: {'포함' if options.category_descriptions else '미포함'}"
        )
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
            run_mode(
                mode, mode_out, selections_by_mode[mode], data, categories,
                definitions, dataset_type, project_config, pricing, settings,
                options.repeat, options.write_url_summary,
            )
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
