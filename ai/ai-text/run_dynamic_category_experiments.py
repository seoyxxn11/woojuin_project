from __future__ import annotations

import argparse
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import main as base_runner
from src.dataset_loader import load_category_definitions, load_flat_test_dataset
from src.dynamic_category_experiment import (
    SCENARIOS,
    CategoryCatalog,
    DynamicCategoryScenario,
    build_dynamic_prompt,
    content_summary,
    dynamic_category_schema,
    parse_dynamic_response,
    resolve_scenarios,
    seed_definitions,
)
from src.model_config import (
    ModelConfig,
    ModelConfigError,
    ModelSelection,
    PricingConfig,
    calculate_cost,
    load_models,
    load_pricing,
    safe_filename,
    select_models,
)
from src.providers import ModelRequest, ModelResponse, sanitize_error
from src.result_writer import write_json
from src.settings import Settings, load_settings


ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET_ROOT = ROOT / "dataset" / "tester" / "정우현"
PROMPT_PATH = ROOT / "prompts" / "dynamic-category-prompt-v1.txt"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="기존 카테고리와 AI 생성 카테고리를 조합하는 동적 분류 실험"
    )
    parser.add_argument(
        "--scenario",
        nargs="+",
        help=(
            "실행 조건: existing11-ai, ai-only, existing3-ai, existing5-ai, "
            "existing7-ai, cumulative, baseline11, reduced-ai, all 또는 번호 0~6"
        ),
    )
    parser.add_argument("--list-scenarios", action="store_true")
    parser.add_argument("--model", default="openrouter-qwen3-8b")
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument(
        "--input-type",
        nargs="+",
        choices=("url", "image", "memo", "all"),
        default=["url"],
    )
    parser.add_argument("--test-ids", nargs="+")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument(
        "--cumulative-seed-count",
        type=int,
        choices=(0, 3, 5, 7, 11),
        default=0,
        help="cumulative 실행을 시작할 기존 카테고리 개수 (기본: 0)",
    )
    parser.add_argument("--category-definitions", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def print_scenarios() -> None:
    print("동적 카테고리 실험 조건")
    for index, scenario in enumerate(SCENARIOS.values()):
        suffix = " (순차 실행)" if scenario.accumulate else ""
        print(f"  {index}. {scenario.id:<15} {scenario.label}{suffix}")
    print("  7. reduced-ai      기존 3개/5개/7개 조건을 연속 실행")
    print("  8. all             기준 테스트를 포함한 모든 조건 실행")


def interactive_scenarios(input_func: Callable[[str], str] = input) -> list[str]:
    print_scenarios()
    value = input_func("실행할 번호 또는 이름을 입력하세요: ").strip()
    if value == "7":
        return ["reduced-ai"]
    if value == "8":
        return ["all"]
    return value.replace(",", " ").split()


def planned_output(model_id: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = ROOT / "results" / f"{timestamp}-dynamic-categories-{safe_filename(model_id)}"
    candidate = base
    suffix = 1
    while candidate.exists():
        candidate = Path(f"{base}-{suffix}")
        suffix += 1
    return candidate


def load_data(options: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dataset_root = options.dataset_root.resolve()
    data, dataset_categories = load_flat_test_dataset(dataset_root, options.input_type)
    definitions_path = (
        options.category_definitions.resolve()
        if options.category_definitions
        else ROOT / "config" / "categories.json"
    )
    definitions = load_category_definitions(definitions_path)
    category_names = set(dataset_categories)
    definitions = [item for item in definitions if item["name"] in category_names]
    missing_definitions = category_names - {item["name"] for item in definitions}
    if missing_definitions:
        raise ValueError(f"설명이 없는 데이터셋 카테고리: {sorted(missing_definitions)}")
    if options.test_ids:
        requested = set(options.test_ids)
        known = {item["testId"] for item in data}
        unknown = sorted(requested - known)
        if unknown:
            raise ValueError(f"존재하지 않는 testId: {', '.join(unknown)}")
        data = [item for item in data if item["testId"] in requested]
    if options.limit is not None:
        if options.limit < 1:
            raise ValueError("--limit은 1 이상이어야 합니다.")
        data = data[: options.limit]
    before = len(data)
    data = [item for item in data if base_runner.category_classification_eligible(item)]
    if before != len(data):
        print(f"[INFO] 사용할 수 있는 URL 요약이 없어 제외: {before - len(data)}건")
    if not data:
        raise ValueError("동적 카테고리 실험에 사용할 데이터가 없습니다.")
    return data, definitions


def select_model(
    model_id: str,
    project_config: dict[str, Any],
    settings: Settings,
    *,
    preflight: bool,
) -> tuple[ModelConfig, Any | None]:
    models = load_models(ROOT / "config" / "models.yaml")
    selections = select_models(models, [model_id], "category-only")
    selection = selections[0]
    if selection.status != "READY" or selection.config is None:
        raise ModelConfigError(selection.error_message or f"모델을 사용할 수 없습니다: {model_id}")
    config = selection.config
    if not preflight:
        return config, None
    providers = base_runner.make_providers(project_config, settings, {config.provider})
    api_key_env = project_config.get("openai", {}).get("apiKeyEnv", "OPENAI_API_KEY")
    checked = base_runner.preflight(selections, providers, settings, api_key_env)[0]
    if checked.status != "READY":
        raise ModelConfigError(checked.error_message or checked.error_type or "모델 사전 점검 실패")
    return config, providers[config.provider]


def generate_safely(provider: Any, request: ModelRequest, config: ModelConfig) -> ModelResponse:
    try:
        return provider.generate(request, config)
    except Exception as exc:
        return ModelResponse(
            provider=config.provider,
            model_id=config.id,
            requested_model=config.model,
            status="FAILED",
            error_type="UNKNOWN_ERROR",
            error_message=sanitize_error(exc),
        )


def request_for(
    item: dict[str, Any],
    definitions: list[dict[str, Any]],
    prompt_template: str,
    temperature: float | None,
) -> ModelRequest:
    content = base_runner.model_input_for_mode(item, "category-only")
    prompt = build_dynamic_prompt(
        prompt_template,
        content,
        str(item.get("title", "")),
        definitions,
    )
    return ModelRequest(
        prompt=prompt,
        schema=dynamic_category_schema(),
        test_mode="dynamic-category",
        test_id=str(item["testId"]),
        temperature=temperature,
    )


def execute_scenario(
    scenario: DynamicCategoryScenario,
    output: Path,
    data: list[dict[str, Any]],
    all_definitions: list[dict[str, Any]],
    config: ModelConfig,
    provider: Any,
    project_config: dict[str, Any],
    pricing: PricingConfig,
    concurrency: int,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    seeds = seed_definitions(all_definitions, scenario.seed_count)
    prompt_catalog = CategoryCatalog(seeds)
    result_catalog = prompt_catalog if scenario.accumulate else CategoryCatalog(seeds)
    started = datetime.now().astimezone()
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    def finish_item(
        item: dict[str, Any],
        response: ModelResponse,
        available: list[dict[str, Any]],
        request_number: int,
    ) -> None:
        info = parse_dynamic_response(response.raw_text, available)
        status = response.status
        error_type = response.error_type or ""
        error_message = response.error_message or ""
        if status == "SUCCESS" and not info["jsonValid"]:
            status, error_type = "FAILED", "JSON_PARSE_ERROR"
            error_message = info["validationError"]
        elif status == "SUCCESS" and not info["schemaValid"]:
            status, error_type = "FAILED", "SCHEMA_ERROR"
            error_message = info["validationError"]

        parsed = info.get("parsedResponse") or {}
        category: dict[str, Any] | None = None
        created = False
        if status == "SUCCESS":
            if parsed["categoryOrigin"] == "EXISTING":
                category = next(
                    item_definition
                    for item_definition in available
                    if str(item_definition["name"]).casefold()
                    == str(parsed["categoryName"]).casefold()
                )
            else:
                category, created = result_catalog.add_generated(
                    parsed["categoryName"], parsed["categoryDescription"]
                )
                if scenario.accumulate:
                    prompt_catalog.add_generated(
                        parsed["categoryName"], parsed["categoryDescription"]
                    )
            if info["deduplicatedToExisting"]:
                category = result_catalog.find(parsed["categoryName"])

        response_dict = response.to_dict()
        response_dict["status"] = status
        response_dict["errorType"] = error_type or None
        response_dict["errorMessage"] = sanitize_error(error_message) if error_message else None
        cost = calculate_cost(pricing, config.id, response.input_tokens, response.output_tokens)
        row = {
            "testId": item["testId"],
            "title": item.get("title", ""),
            "sourcePath": item.get("sourcePath", ""),
            "inputType": item.get("inputType", ""),
            "summary": content_summary(str(item.get("input", ""))),
            "generatedSummary": content_summary(str(item.get("input", ""))),
            "generatedCategory": category["name"] if category else "",
            "aiCategory": (
                {"id": category["id"], "name": category["name"]}
                if category else None
            ),
            "aiReason": parsed.get("reason", ""),
            "categoryDescription": parsed.get("categoryDescription", ""),
            "categoryOrigin": parsed.get("categoryOrigin", ""),
            "categoryCreatedNow": created,
            "availableCategories": [definition["name"] for definition in available],
            "availableCategoryCount": len(available),
            "scenario": scenario.id,
            "scenarioLabel": scenario.label,
            "modelId": config.id,
            "provider": config.provider,
            "requestedModel": config.model,
            "status": status,
            "errorType": error_type,
            "errorMessage": sanitize_error(error_message) if error_message else "",
            "latencyMs": response.latency_ms,
            "inputTokens": response.input_tokens,
            "outputTokens": response.output_tokens,
            "totalTokens": response.total_tokens,
            "estimatedCost": cost,
            "parsedResponse": parsed or None,
            "executedAt": datetime.now().astimezone().isoformat(),
        }
        rows.append(row)
        write_json(
            output / "raw-responses" / f"{safe_filename(str(item['testId']))}.json",
            {
                "testId": item["testId"],
                "availableCategories": row["availableCategories"],
                "response": response_dict,
                "parsing": info,
                "estimatedCost": cost,
            },
        )
        if status != "SUCCESS":
            failures.append(
                {
                    "testId": item["testId"],
                    "errorType": error_type,
                    "errorMessage": sanitize_error(error_message),
                }
            )
        print(
            f"[{request_number}/{len(data)}] {item['testId']} "
            f"{status} | {row['generatedCategory'] or error_type}"
        )

    if scenario.accumulate:
        print("[INFO] 누적 조건은 이전 결과를 다음 요청에 넣기 위해 동시 요청 수를 1로 적용합니다.")
        for index, item in enumerate(data, start=1):
            available = prompt_catalog.definitions
            response = generate_safely(
                provider,
                request_for(item, available, prompt_template, project_config.get("temperature")),
                config,
            )
            finish_item(item, response, available, index)
        applied_concurrency = 1
    else:
        available = prompt_catalog.definitions
        requests = [
            request_for(item, available, prompt_template, project_config.get("temperature"))
            for item in data
        ]
        applied_concurrency = concurrency if config.provider in {"openai", "openrouter"} else 1
        if applied_concurrency > 1:
            with ThreadPoolExecutor(
                max_workers=applied_concurrency,
                thread_name_prefix=f"{safe_filename(config.id)}-dynamic",
            ) as executor:
                responses = list(
                    executor.map(
                        lambda request: generate_safely(provider, request, config), requests
                    )
                )
        else:
            responses = [generate_safely(provider, request, config) for request in requests]
        for index, (item, response) in enumerate(zip(data, responses), start=1):
            finish_item(item, response, available, index)

    completed = datetime.now().astimezone()
    categories = result_catalog.definitions
    successful = [row for row in rows if row["status"] == "SUCCESS"]
    generated = [row for row in successful if row["categoryOrigin"] == "GENERATED"]
    metadata = {
        "testMode": "dynamic-category",
        "scenario": scenario.id,
        "scenarioLabel": scenario.label,
        "seedCategoryCount": scenario.seed_count,
        "seedCategories": [item["name"] for item in seeds],
        "accumulateGeneratedCategories": scenario.accumulate,
        "datasetCount": len(data),
        "modelId": config.id,
        "provider": config.provider,
        "requestedModel": config.model,
        "promptFile": PROMPT_PATH.name,
        "promptVersion": "v1",
        "concurrencyRequested": concurrency,
        "concurrencyApplied": applied_concurrency,
        "startedAt": started.isoformat(),
        "completedAt": completed.isoformat(),
        "status": "COMPLETED" if not failures else "COMPLETED_WITH_FAILURES",
        "successCount": len(successful),
        "failureCount": len(failures),
        "existingSelectionCount": sum(
            row["categoryOrigin"] == "EXISTING" for row in successful
        ),
        "generatedSelectionCount": len(generated),
        "finalCategoryCount": len(categories),
        "finalCategories": [item["name"] for item in categories],
    }
    write_json(output / "run-metadata.json", metadata)
    write_json(output / "evaluation-results.json", rows)
    write_json(
        output / "review-draft.json",
        {
            "scenario": scenario.id,
            "scenarioLabel": scenario.label,
            "categories": categories,
            "items": rows,
        },
    )
    write_json(output / "failures.json", failures)
    write_csv(output / "results.csv", rows)
    write_report(output / "report.md", metadata, categories)
    return metadata


def execute_baseline(
    scenario: DynamicCategoryScenario,
    output: Path,
    data: list[dict[str, Any]],
    definitions: list[dict[str, Any]],
    config: ModelConfig,
    project_config: dict[str, Any],
    pricing: PricingConfig,
    settings: Settings,
    concurrency: int,
) -> dict[str, Any]:
    """기존 main.py의 고정 카테고리 분류 코드를 그대로 호출한다."""
    categories = [str(item["name"]) for item in definitions]
    base_runner.run_mode(
        "category-only",
        output,
        [ModelSelection(config.id, config)],
        data,
        categories,
        definitions,
        "dynamic-baseline",
        project_config,
        pricing,
        settings,
        1,
        False,
        concurrency,
    )
    metadata_path = output / "run-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["scenario"] = scenario.id
    metadata["scenarioLabel"] = scenario.label
    metadata["baselineImplementation"] = "main.py run_mode(category-only)"
    write_json(metadata_path, metadata)
    return {
        "testMode": "category-only",
        "scenario": scenario.id,
        "scenarioLabel": scenario.label,
        "datasetCount": len(data),
        "modelId": config.id,
        "provider": config.provider,
        "requestedModel": config.model,
        "status": metadata.get("status"),
        "seedCategoryCount": len(definitions),
        "seedCategories": categories,
        "accumulateGeneratedCategories": False,
        "output": str(output),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "testId",
        "title",
        "sourcePath",
        "generatedCategory",
        "categoryOrigin",
        "categoryCreatedNow",
        "availableCategoryCount",
        "aiReason",
        "status",
        "errorType",
        "latencyMs",
        "inputTokens",
        "outputTokens",
        "estimatedCost",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    path: Path, metadata: dict[str, Any], categories: list[dict[str, Any]]
) -> None:
    lines = [
        f"# 동적 카테고리 실험: {metadata['scenarioLabel']}",
        "",
        f"- 모델: {metadata['modelId']} ({metadata['requestedModel']})",
        f"- 데이터: {metadata['datasetCount']}건",
        f"- 성공/실패: {metadata['successCount']} / {metadata['failureCount']}",
        f"- 기존 카테고리 선택: {metadata['existingSelectionCount']}건",
        f"- 새 카테고리 생성 선택: {metadata['generatedSelectionCount']}건",
        f"- 시작 카테고리: {metadata['seedCategoryCount']}개",
        f"- 최종 카테고리: {metadata['finalCategoryCount']}개",
        f"- 생성 카테고리 누적: {'예' if metadata['accumulateGeneratedCategories'] else '아니오'}",
        "",
        "## 최종 카테고리",
        "",
        "| 구분 | 이름 | 설명 |",
        "|---|---|---|",
    ]
    lines.extend(
        f"| {'AI 생성' if item.get('origin') == 'AI_GENERATED' else '기존'} "
        f"| {item['name']} | {str(item.get('description', '')).replace('|', '\\|')} |"
        for item in categories
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    options = parse_args(argv)
    try:
        if options.list_scenarios:
            print_scenarios()
            return 0
        if options.concurrency < 1:
            raise ValueError("--concurrency는 1 이상이어야 합니다.")
        scenario_values = options.scenario
        if not scenario_values:
            if not sys.stdin.isatty():
                raise ValueError("--scenario로 실행 조건을 선택하세요. 목록: --list-scenarios")
            scenario_values = interactive_scenarios()
        scenarios = resolve_scenarios(scenario_values)
        scenarios = [
            replace(scenario, seed_count=options.cumulative_seed_count)
            if scenario.id == "cumulative"
            else scenario
            for scenario in scenarios
        ]
        data, definitions = load_data(options)
        project_config = base_runner.load_project_config()
        settings = load_settings(ROOT)
        config, provider = select_model(
            options.model, project_config, settings, preflight=not options.dry_run
        )
        output = options.output.resolve() if options.output else planned_output(config.id)
        if output.exists():
            raise ValueError(f"결과 폴더가 이미 존재합니다: {output}")

        print(f"[OK] 모델: {config.id} ({config.provider} / {config.model})")
        print(f"[OK] 데이터: {len(data)}건")
        for scenario in scenarios:
            seeds = seed_definitions(definitions, scenario.seed_count)
            print(
                f"[조건] {scenario.id}: {scenario.label} | "
                f"시작 카테고리 {len(seeds)}개 | "
                f"누적 {'예' if scenario.accumulate else '아니오'}"
            )
            if seeds:
                print(f"       {', '.join(item['name'] for item in seeds)}")
        print(f"[OK] 예상 API 요청: {len(data) * len(scenarios)}회")
        print(f"[OK] 결과 상위 폴더: {output}")
        if options.dry_run:
            print("[DRY-RUN] API 호출과 결과 파일 생성을 수행하지 않았습니다.")
            return 0

        output.mkdir(parents=True)
        pricing = load_pricing(ROOT / "config" / "model-pricing.yaml")
        summaries: list[dict[str, Any]] = []
        assert provider is not None
        for index, scenario in enumerate(scenarios, start=1):
            print(f"\n[SCENARIO {index}/{len(scenarios)}] {scenario.id}")
            if scenario.baseline:
                summaries.append(
                    execute_baseline(
                        scenario,
                        output / scenario.id,
                        data,
                        definitions,
                        config,
                        project_config,
                        pricing,
                        settings,
                        options.concurrency,
                    )
                )
            else:
                summaries.append(execute_scenario(
                    scenario,
                    output / scenario.id,
                    data,
                    definitions,
                    config,
                    provider,
                    project_config,
                    pricing,
                    options.concurrency,
                ))
        write_json(
            output / "run-summary.json",
            {
                "modelId": config.id,
                "datasetRoot": str(options.dataset_root.resolve()),
                "datasetCount": len(data),
                "scenarios": summaries,
            },
        )
        print(f"\n[OK] 모든 동적 카테고리 실험 완료: {output}")
        print(f"[GUI] 상위 폴더로 이 경로를 선택하세요: {output}")
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, ModelConfigError) as exc:
        print(f"[FAIL] {sanitize_error(exc)}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
