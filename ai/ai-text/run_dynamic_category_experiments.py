from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import main as base_runner
from src.dataset_loader import load_category_definitions, load_flat_test_dataset
from src.dynamic_category_experiment import (
    GENERATED_EXISTING,
    NEW_GENERATED,
    SCENARIO_ALIASES,
    SCENARIOS,
    SEED_EXISTING,
    CategoryCatalog,
    DynamicCategoryScenario,
    apply_ordering,
    build_dynamic_prompt,
    classify_selection,
    content_summary,
    dynamic_category_schema,
    find_duplicate_candidates,
    is_generated_origin,
    parse_dynamic_response,
    resolve_orderings,
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
    parser.add_argument(
        "--order",
        nargs="+",
        default=["original"],
        help="데이터 순서: original, shuffle-42, shuffle-84, all (기본: original)",
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
    accumulate_group = parser.add_mutually_exclusive_group()
    accumulate_group.add_argument(
        "--accumulate-generated-categories",
        dest="accumulate",
        action="store_true",
        default=None,
        help="시나리오 기본값과 무관하게 생성 카테고리 누적을 강제로 켭니다.",
    )
    accumulate_group.add_argument(
        "--no-accumulate-generated-categories",
        dest="accumulate",
        action="store_false",
        help="시나리오 기본값과 무관하게 생성 카테고리 누적을 끕니다.",
    )
    parser.add_argument(
        "--resume",
        type=Path,
        help="중단된 상위 결과 폴더를 지정해 완료된 데이터를 건너뛰고 이어서 실행합니다.",
    )
    parser.add_argument("--category-definitions", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def print_scenarios() -> None:
    print("동적 카테고리 실험 조건")
    for scenario in SCENARIOS.values():
        suffix = " (순차 누적)" if scenario.accumulate else ""
        alias = next(
            (key for key, value in SCENARIO_ALIASES.items() if value == scenario.id), " "
        )
        print(f"  {alias}. {scenario.id:<26} {scenario.label}{suffix}")
    print()
    print("  그룹 별칭")
    print("  reduced-ai            기존 3개/5개/7개(비누적) 연속 실행")
    print("  reduced-ai-cumulative 기존 3개/5개/7개 누적 연속 실행")
    print("  cumulative-compare    AI 전용/기존 5개/기존 7개 누적 비교 (목표 조건)")
    print("  all                   기준 테스트를 포함한 기본 조건 실행")


def interactive_scenarios(input_func: Callable[[str], str] = input) -> list[str]:
    print_scenarios()
    value = input_func("실행할 번호 또는 이름을 입력하세요: ").strip()
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


def _progress_path(output: Path) -> Path:
    return output / "progress.jsonl"


def _load_progress_rows(output: Path) -> list[dict[str, Any]]:
    path = _progress_path(output)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            rows.append(json.loads(stripped))
    return rows


def _append_progress(output: Path, row: dict[str, Any]) -> None:
    path = _progress_path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


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
    *,
    order_name: str = "original",
    accumulate: bool | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    accumulate = scenario.accumulate if accumulate is None else bool(accumulate)
    output.mkdir(parents=True, exist_ok=True)
    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    seeds = seed_definitions(all_definitions, scenario.seed_count)
    ordered, order_seed = apply_ordering(data, order_name)
    order_by_id = {str(item["testId"]): index for index, item in enumerate(ordered, start=1)}

    result_catalog = CategoryCatalog(seeds)
    # 누적 조건에서는 프롬프트에 제공하는 후보와 결과 카탈로그가 같은 객체다.
    prompt_catalog = result_catalog if accumulate else CategoryCatalog(seeds)

    started = datetime.now().astimezone()
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    # 재개: 저장된 진행 상황을 순서대로 복원해 누적 카탈로그 상태를 되돌린다.
    completed_ids: set[str] = set()
    if resume:
        for saved in _load_progress_rows(output):
            rows.append(saved)
            completed_ids.add(str(saved["testId"]))
            if saved.get("status") != "SUCCESS":
                failures.append(
                    {
                        "testId": saved["testId"],
                        "errorType": saved.get("errorType", ""),
                        "errorMessage": saved.get("errorMessage", ""),
                    }
                )
            elif (
                saved.get("selectionType") == NEW_GENERATED
                and saved.get("selectedCategoryName")
            ):
                result_catalog.add_generated(
                    saved["selectedCategoryName"],
                    saved.get("categoryDescription", ""),
                    saved.get("createdAtItemId"),
                )
        if completed_ids:
            print(
                f"[RESUME] {scenario.id}_{order_name}: 완료 {len(completed_ids)}건 복원, "
                f"누적 카테고리 {len(result_catalog.definitions)}개"
            )

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
        selection_type = ""
        is_new = False
        if status == "SUCCESS":
            category, selection_type, is_new = classify_selection(
                parsed, available, result_catalog, str(item["testId"])
            )

        response_dict = response.to_dict()
        response_dict["status"] = status
        response_dict["errorType"] = error_type or None
        response_dict["errorMessage"] = sanitize_error(error_message) if error_message else None
        cost = calculate_cost(pricing, config.id, response.input_tokens, response.output_tokens)
        input_order = order_by_id.get(str(item["testId"]), request_number)
        summary_text = content_summary(str(item.get("input", "")))
        row = {
            "testId": item["testId"],
            "itemId": item["testId"],
            "inputOrder": input_order,
            "title": item.get("title", ""),
            "sourcePath": item.get("sourcePath", ""),
            "inputType": item.get("inputType", ""),
            "summary": summary_text,
            "generatedSummary": summary_text,
            "selectionType": selection_type,
            "selectedCategoryId": category["id"] if category else "",
            "selectedCategoryName": category["name"] if category else "",
            "isNewCategory": is_new,
            "categoryOrigin": category.get("origin") if category else "",
            "modelCategoryOrigin": parsed.get("categoryOrigin", ""),
            "categoryDescription": (
                category.get("description")
                if category
                else parsed.get("categoryDescription", "")
            ),
            "createdAtItemId": category.get("createdAtItemId") if category else None,
            "generatedCategory": category["name"] if category else "",
            "aiCategory": (
                {"id": category["id"], "name": category["name"]} if category else None
            ),
            "aiReason": parsed.get("reason", ""),
            "availableCategories": [definition["name"] for definition in available],
            "availableCategoryCount": len(available),
            "scenario": scenario.id,
            "scenarioLabel": scenario.label,
            "order": order_name,
            "modelId": config.id,
            "provider": config.provider,
            "requestedModel": config.model,
            "status": status,
            "success": status == "SUCCESS",
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
        _append_progress(output, row)
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
            f"[{request_number}/{len(ordered)}] {item['testId']} "
            f"{status} | {row['selectedCategoryName'] or error_type} "
            f"({selection_type or '-'})"
        )

    remaining = [item for item in ordered if str(item["testId"]) not in completed_ids]

    if accumulate:
        if len(remaining) == len(ordered):
            print("[INFO] 누적 조건은 이전 결과를 다음 요청에 넣기 위해 동시 요청 수를 1로 적용합니다.")
        for item in remaining:
            available = prompt_catalog.definitions
            response = generate_safely(
                provider,
                request_for(item, available, prompt_template, project_config.get("temperature")),
                config,
            )
            finish_item(item, response, available, order_by_id[str(item["testId"])])
        applied_concurrency = 1
    else:
        available = prompt_catalog.definitions
        requests = [
            request_for(item, available, prompt_template, project_config.get("temperature"))
            for item in remaining
        ]
        applied_concurrency = concurrency if config.provider in {"openai", "openrouter"} else 1
        if applied_concurrency > 1 and requests:
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
        for item, response in zip(remaining, responses):
            finish_item(item, response, available, order_by_id[str(item["testId"])])

    completed = datetime.now().astimezone()
    rows.sort(key=lambda row: row.get("inputOrder", 0))
    return _finalize_scenario(
        scenario,
        output,
        ordered,
        seeds,
        rows,
        failures,
        result_catalog,
        config,
        pricing,
        concurrency,
        applied_concurrency,
        order_name,
        order_seed,
        accumulate,
        started,
        completed,
    )


def _finalize_scenario(
    scenario: DynamicCategoryScenario,
    output: Path,
    ordered: list[dict[str, Any]],
    seeds: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    result_catalog: CategoryCatalog,
    config: ModelConfig,
    pricing: PricingConfig,
    concurrency: int,
    applied_concurrency: int,
    order_name: str,
    order_seed: int | None,
    accumulate: bool,
    started: datetime,
    completed: datetime,
) -> dict[str, Any]:
    successful = [row for row in rows if row["status"] == "SUCCESS"]
    counts = Counter(
        row["selectedCategoryId"] for row in successful if row["selectedCategoryId"]
    )
    categories = result_catalog.definitions
    for category in categories:
        category["selectedItemCount"] = counts.get(category["id"], 0)

    seed_existing = sum(row["selectionType"] == SEED_EXISTING for row in successful)
    generated_existing = sum(row["selectionType"] == GENERATED_EXISTING for row in successful)
    new_generated = sum(row["selectionType"] == NEW_GENERATED for row in successful)
    total = len(successful) or 1

    generated_categories = [c for c in categories if is_generated_origin(c.get("origin"))]
    single_use = [c for c in categories if c["selectedItemCount"] == 1]
    reused_generated = [c for c in generated_categories if c["selectedItemCount"] >= 2]
    used_categories = [c for c in categories if c["selectedItemCount"] > 0]
    most_used = max(categories, key=lambda c: c["selectedItemCount"], default=None)
    if most_used is not None and most_used["selectedItemCount"] == 0:
        most_used = None
    duplicate_candidates = find_duplicate_candidates(categories)
    elapsed = (completed - started).total_seconds()

    summary = {
        "successCount": len(successful),
        "failureCount": len(failures),
        "initialCategoryCount": len(seeds),
        "finalCategoryCount": len(categories),
        "seedExistingCount": seed_existing,
        "generatedExistingCount": generated_existing,
        "newGeneratedCount": new_generated,
        "seedSelectionRatio": round(seed_existing / total, 4),
        "generatedReuseRatio": round(generated_existing / total, 4),
        "newGenerationRatio": round(new_generated / total, 4),
        "singleUseCategoryCount": len(single_use),
        "reusedGeneratedCategoryCount": len(reused_generated),
        "usedCategoryCount": len(used_categories),
        "mostUsedCategory": (
            {"name": most_used["name"], "selectedItemCount": most_used["selectedItemCount"]}
            if most_used
            else None
        ),
        "avgItemsPerCategory": (
            round(len(successful) / len(categories), 4) if categories else 0.0
        ),
        "largestCategoryShare": (
            round(most_used["selectedItemCount"] / total, 4) if most_used else 0.0
        ),
        "elapsedSeconds": round(elapsed, 3),
    }
    metadata = {
        "testMode": "dynamic-category",
        "scenario": scenario.id,
        "scenarioLabel": scenario.label,
        "order": order_name,
        "randomSeed": order_seed,
        "accumulateGeneratedCategories": accumulate,
        "seedCategoryCount": scenario.seed_count,
        "seedCategories": [item["name"] for item in seeds],
        "datasetCount": len(ordered),
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
        "existingSelectionCount": seed_existing + generated_existing,
        "generatedSelectionCount": new_generated,
        "finalCategoryCount": len(categories),
        "finalCategories": [item["name"] for item in categories],
        "duplicateCandidateCount": len(duplicate_candidates),
        **summary,
    }
    result_payload = {
        "runConfig": {
            "scenario": scenario.id,
            "scenarioLabel": scenario.label,
            "modelId": config.id,
            "provider": config.provider,
            "requestedModel": config.model,
            "datasetCount": len(ordered),
            "order": order_name,
            "randomSeed": order_seed,
            "accumulateGeneratedCategories": accumulate,
            "seedCategoryCount": len(seeds),
            "seedCategories": [item["name"] for item in seeds],
            "promptFile": PROMPT_PATH.name,
            "promptVersion": "v1",
            "startedAt": started.isoformat(),
            "completedAt": completed.isoformat(),
            "status": metadata["status"],
        },
        "summary": summary,
        "categories": categories,
        "items": rows,
        "duplicateCandidates": duplicate_candidates,
    }

    write_json(output / "run-metadata.json", metadata)
    write_json(output / "result.json", result_payload)
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
    write_items_csv(output / "items.csv", rows)
    write_categories_csv(output / "categories.csv", categories)
    (output / "report.md").write_text(
        build_report(metadata, summary, categories, duplicate_candidates, markdown=True),
        encoding="utf-8",
    )
    (output / "report.txt").write_text(
        build_report(metadata, summary, categories, duplicate_candidates, markdown=False),
        encoding="utf-8",
    )
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
    *,
    order_name: str = "original",
) -> dict[str, Any]:
    """기존 main.py의 고정 카테고리 분류 코드를 그대로 호출한다."""
    categories = [str(item["name"]) for item in definitions]
    ordered, order_seed = apply_ordering(data, order_name)
    base_runner.run_mode(
        "category-only",
        output,
        [ModelSelection(config.id, config)],
        ordered,
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
    metadata["order"] = order_name
    metadata["randomSeed"] = order_seed
    metadata["baselineImplementation"] = "main.py run_mode(category-only)"
    write_json(metadata_path, metadata)
    return {
        "testMode": "category-only",
        "scenario": scenario.id,
        "scenarioLabel": scenario.label,
        "order": order_name,
        "randomSeed": order_seed,
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


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """기존 호환용 상세 결과 CSV."""
    _write_csv(
        path,
        [
            "testId",
            "inputOrder",
            "title",
            "sourcePath",
            "selectionType",
            "generatedCategory",
            "categoryOrigin",
            "isNewCategory",
            "availableCategoryCount",
            "aiReason",
            "status",
            "errorType",
            "latencyMs",
            "inputTokens",
            "outputTokens",
            "estimatedCost",
        ],
        rows,
    )


def write_items_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_csv(
        path,
        [
            "itemId",
            "inputOrder",
            "selectionType",
            "selectedCategoryId",
            "selectedCategoryName",
            "isNewCategory",
            "categoryOrigin",
            "success",
            "errorMessage",
        ],
        rows,
    )


def write_categories_csv(path: Path, categories: list[dict[str, Any]]) -> None:
    mapped = [
        {
            "categoryId": category.get("id", ""),
            "categoryName": category.get("name", ""),
            "description": category.get("description", ""),
            "origin": category.get("origin", ""),
            "createdAtItemId": category.get("createdAtItemId"),
            "selectedItemCount": category.get("selectedItemCount", 0),
        }
        for category in categories
    ]
    _write_csv(
        path,
        [
            "categoryId",
            "categoryName",
            "description",
            "origin",
            "createdAtItemId",
            "selectedItemCount",
        ],
        mapped,
    )


def _cell(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def build_report(
    metadata: dict[str, Any],
    summary: dict[str, Any],
    categories: list[dict[str, Any]],
    duplicate_candidates: list[dict[str, Any]],
    *,
    markdown: bool,
) -> str:
    """시나리오별 보고서 본문을 Markdown 또는 일반 텍스트로 생성한다."""

    def heading(level: int, text: str) -> str:
        return f"{'#' * level} {text}" if markdown else text

    most_used = summary.get("mostUsedCategory")
    most_used_text = (
        f"{most_used['name']} ({most_used['selectedItemCount']}건)" if most_used else "없음"
    )
    lines: list[str] = [
        heading(1, f"동적 카테고리 실험: {metadata['scenarioLabel']}"),
        "",
        heading(2, "실행 정보"),
        f"- 모델 ID: {metadata['modelId']} ({metadata['requestedModel']})",
        f"- 데이터셋 개수: {metadata['datasetCount']}",
        f"- 실행 순서: {metadata['order']}",
        f"- 랜덤 시드: {metadata['randomSeed']}",
        f"- 생성 카테고리 누적: {'예' if metadata['accumulateGeneratedCategories'] else '아니오'}",
        f"- 성공 수: {summary['successCount']}",
        f"- 실패 수: {summary['failureCount']}",
        f"- 초기 카테고리 수: {summary['initialCategoryCount']}",
        f"- 최종 카테고리 수: {summary['finalCategoryCount']}",
        "",
        heading(2, "선택 결과"),
        f"- 초기 기존 카테고리 선택 수: {summary['seedExistingCount']}",
        f"- AI 생성 카테고리 재사용 수: {summary['generatedExistingCount']}",
        f"- 신규 카테고리 생성 수: {summary['newGeneratedCount']}",
        "",
        heading(2, "비율"),
        f"- 기존 카테고리 선택 비율: {summary['seedSelectionRatio']:.1%}",
        f"- 생성 카테고리 재사용 비율: {summary['generatedReuseRatio']:.1%}",
        f"- 신규 생성 비율: {summary['newGenerationRatio']:.1%}",
        "",
        heading(2, "카테고리 사용 분포"),
    ]
    if markdown:
        lines.append("| ID | 이름 | 설명 | 출처 | 선택 수 | 최초 생성 데이터 |")
        lines.append("|---|---|---|---|--:|---|")
        for item in categories:
            lines.append(
                f"| {_cell(item.get('id'))} | {_cell(item.get('name'))} "
                f"| {_cell(item.get('description'))} | {_cell(item.get('origin'))} "
                f"| {item.get('selectedItemCount', 0)} | {_cell(item.get('createdAtItemId'))} |"
            )
    else:
        for item in categories:
            lines.append(
                f"- [{_cell(item.get('origin'))}] {_cell(item.get('name'))} "
                f"(선택 {item.get('selectedItemCount', 0)}건, 최초 {_cell(item.get('createdAtItemId')) or '-'}) "
                f": {_cell(item.get('description'))}"
            )
    lines.extend(
        [
            "",
            heading(2, "카테고리 사용 요약"),
            f"- 1회만 사용된 카테고리 수: {summary['singleUseCategoryCount']}",
            f"- 2회 이상 재사용된 생성 카테고리 수: {summary['reusedGeneratedCategoryCount']}",
            f"- 가장 많이 사용된 카테고리: {most_used_text}",
            f"- 카테고리당 평균 데이터 수: {summary['avgItemsPerCategory']}",
            f"- 가장 큰 카테고리의 데이터 비율: {summary['largestCategoryShare']:.1%}",
            "",
            heading(2, f"중복 검토 후보 ({len(duplicate_candidates)}건)"),
        ]
    )
    if not duplicate_candidates:
        lines.append("- 없음")
    elif markdown:
        lines.append("| 카테고리 | 공통 단어 | 사유 |")
        lines.append("|---|---|---|")
        for candidate in duplicate_candidates:
            names = ", ".join(candidate["categories"])
            shared = ", ".join(candidate.get("sharedTokens", []))
            lines.append(f"| {_cell(names)} | {_cell(shared)} | {_cell(candidate['reason'])} |")
    else:
        for candidate in duplicate_candidates:
            names = " / ".join(candidate["categories"])
            lines.append(f"- {names}: {candidate['reason']}")
    return "\n".join(lines) + "\n"


def resolve_accumulate(scenario: DynamicCategoryScenario, override: bool | None) -> bool:
    return scenario.accumulate if override is None else bool(override)


COMPARISON_COLUMNS = [
    ("scenario", "시나리오"),
    ("order", "순서"),
    ("accumulate", "누적"),
    ("initialCategoryCount", "초기 카테고리 수"),
    ("finalCategoryCount", "최종 카테고리 수"),
    ("newGeneratedCount", "신규 생성 수"),
    ("generatedExistingCount", "생성 재사용 수"),
    ("singleUseCategoryCount", "1회 사용 카테고리 수"),
    ("avgItemsPerCategory", "카테고리당 평균 데이터"),
    ("largestCategoryShare", "최대 카테고리 비율"),
    ("failureCount", "실패 수"),
    ("elapsedSeconds", "실행 시간(초)"),
]


def _comparison_record(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "scenario": summary.get("scenario", ""),
        "order": summary.get("order", ""),
        "accumulate": summary.get("accumulateGeneratedCategories", ""),
        "initialCategoryCount": summary.get(
            "initialCategoryCount", summary.get("seedCategoryCount", "")
        ),
        "finalCategoryCount": summary.get("finalCategoryCount", ""),
        "newGeneratedCount": summary.get("newGeneratedCount", ""),
        "generatedExistingCount": summary.get("generatedExistingCount", ""),
        "singleUseCategoryCount": summary.get("singleUseCategoryCount", ""),
        "avgItemsPerCategory": summary.get("avgItemsPerCategory", ""),
        "largestCategoryShare": summary.get("largestCategoryShare", ""),
        "failureCount": summary.get("failureCount", ""),
        "elapsedSeconds": summary.get("elapsedSeconds", ""),
        "newGenerationRatio": summary.get("newGenerationRatio", ""),
    }


def write_comparison_report(output: Path, summaries: list[dict[str, Any]]) -> None:
    records = [_comparison_record(summary) for summary in summaries]
    _write_csv(output / "comparison.csv", [key for key, _ in COMPARISON_COLUMNS], records)

    keys = [key for key, _ in COMPARISON_COLUMNS]
    headers = [label for _, label in COMPARISON_COLUMNS]
    lines = [
        "# 동적 카테고리 실험 통합 비교",
        "",
        "## 시나리오 × 데이터 순서 비교",
        "",
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for record in records:
        lines.append("| " + " | ".join(_cell(record[key]) for key in keys) + " |")

    # 같은 시나리오가 데이터 순서에 따라 얼마나 달라지는지 요약한다.
    by_scenario: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_scenario.setdefault(record["scenario"], []).append(record)
    lines.extend(["", "## 데이터 순서에 따른 변동 (같은 시나리오)", ""])
    lines.append("| 시나리오 | 순서 수 | 최종 카테고리 수(순서별) | 신규 생성 비율(순서별) |")
    lines.append("|---|--:|---|---|")
    for scenario_id, group in by_scenario.items():
        finals = ", ".join(
            f"{item['order']}={item['finalCategoryCount']}" for item in group
        )
        ratios = ", ".join(
            f"{item['order']}={item['newGenerationRatio']}" for item in group
        )
        lines.append(f"| {scenario_id} | {len(group)} | {finals} | {ratios} |")

    (output / "comparison-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        orders = resolve_orderings(options.order)
        data, definitions = load_data(options)
        project_config = base_runner.load_project_config()
        settings = load_settings(ROOT)
        config, provider = select_model(
            options.model, project_config, settings, preflight=not options.dry_run
        )

        resuming = options.resume is not None
        if resuming:
            output = options.resume.resolve()
            if not output.exists():
                raise ValueError(f"재개할 결과 폴더가 없습니다: {output}")
        elif options.output:
            output = options.output.resolve()
            if output.exists():
                raise ValueError(f"결과 폴더가 이미 존재합니다: {output}")
        else:
            output = planned_output(config.id)

        print(f"[OK] 모델: {config.id} ({config.provider} / {config.model})")
        print(f"[OK] 데이터: {len(data)}건 | 순서: {', '.join(orders)}")
        if resuming:
            print(f"[RESUME] 상위 폴더: {output}")
        for scenario in scenarios:
            seeds = seed_definitions(definitions, scenario.seed_count)
            accumulate = resolve_accumulate(scenario, options.accumulate)
            print(
                f"[조건] {scenario.id}: {scenario.label} | "
                f"시작 카테고리 {len(seeds)}개 | "
                f"누적 {'예' if accumulate else '아니오'}"
                + (" (CLI 강제)" if options.accumulate is not None and not scenario.baseline else "")
            )
            if seeds:
                print(f"       {', '.join(item['name'] for item in seeds)}")
        run_units = [
            (scenario, order) for scenario in scenarios for order in orders
        ]
        print(f"[OK] 실행 조합: {len(run_units)}개 (시나리오 {len(scenarios)} × 순서 {len(orders)})")
        print(f"[OK] 예상 API 요청: {len(data) * len(run_units)}회")
        print(f"[OK] 결과 상위 폴더: {output}")
        if options.dry_run:
            for scenario, order in run_units:
                print(f"  - {scenario.id}_{order}")
            print("[DRY-RUN] API 호출과 결과 파일 생성을 수행하지 않았습니다.")
            return 0

        output.mkdir(parents=True, exist_ok=resuming)
        pricing = load_pricing(ROOT / "config" / "model-pricing.yaml")
        summaries: list[dict[str, Any]] = []
        assert provider is not None
        for index, (scenario, order) in enumerate(run_units, start=1):
            subdir = output / f"{scenario.id}_{order}"
            accumulate = resolve_accumulate(scenario, options.accumulate)
            print(f"\n[RUN {index}/{len(run_units)}] {scenario.id}_{order}")
            if scenario.baseline:
                if resuming and (subdir / "run-metadata.json").exists():
                    print("[RESUME] 기준 조건은 이미 완료되어 건너뜁니다.")
                    metadata = json.loads(
                        (subdir / "run-metadata.json").read_text(encoding="utf-8")
                    )
                    summaries.append(
                        {
                            "scenario": scenario.id,
                            "order": order,
                            "status": metadata.get("status"),
                            "accumulateGeneratedCategories": False,
                            "output": str(subdir),
                        }
                    )
                    continue
                summaries.append(
                    execute_baseline(
                        scenario,
                        subdir,
                        data,
                        definitions,
                        config,
                        project_config,
                        pricing,
                        settings,
                        options.concurrency,
                        order_name=order,
                    )
                )
            else:
                resume_this = resuming and _progress_path(subdir).exists()
                summaries.append(
                    execute_scenario(
                        scenario,
                        subdir,
                        data,
                        definitions,
                        config,
                        provider,
                        project_config,
                        pricing,
                        options.concurrency,
                        order_name=order,
                        accumulate=accumulate,
                        resume=resume_this,
                    )
                )
        write_json(
            output / "run-summary.json",
            {
                "modelId": config.id,
                "datasetRoot": str(options.dataset_root.resolve()),
                "datasetCount": len(data),
                "orders": orders,
                "accumulateOverride": options.accumulate,
                "scenarios": summaries,
            },
        )
        write_comparison_report(output, summaries)
        print(f"\n[OK] 모든 동적 카테고리 실험 완료: {output}")
        print(f"[비교] {output / 'comparison-report.md'}")
        print(f"[GUI] 상위 폴더로 이 경로를 선택하세요: {output}")
        return 0
    except KeyboardInterrupt:
        print("\n[중단] 진행 상황은 저장되었습니다. --resume 로 이어서 실행하세요.")
        return 130
    except (OSError, ValueError, ModelConfigError) as exc:
        print(f"[FAIL] {sanitize_error(exc)}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
