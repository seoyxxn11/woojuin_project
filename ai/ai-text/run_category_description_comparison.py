from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

import run_classification_experiment as classification
from src.dataset_loader import load_categories, load_category_definitions, load_memo_dataset
from src.ollama_client import OllamaClient
from src.prompt_builder import build_prompt, load_prompt
from src.result_writer import write_csv, write_json


ROOT = Path(__file__).resolve().parent
RESULTS_ROOT = ROOT / "results" / "5차 카테고리 설명 비교"
PROMPT_PATH = ROOT / "prompts" / "experiment-category-prompt-v1.txt"


@dataclass(frozen=True)
class Condition:
    id: str
    label: str
    definitions_source: str
    include_descriptions: bool


CONDITIONS = (
    Condition("ai-generated-description", "AI 생성 설명", "generated", True),
    Condition("existing-description", "기존 설명", "existing", True),
    Condition("names-only", "카테고리 이름만", "existing", False),
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI 생성 설명·기존 설명·이름만 분류 정확도 비교")
    parser.add_argument("--generated-definitions", required=True, help="AI가 생성한 카테고리 정의 JSON")
    parser.add_argument("--threshold", type=float, default=None, help="평가 임계값, 기본 config.yaml 값")
    parser.add_argument("--limit", type=int, help="앞에서부터 일부 메모만 실행")
    parser.add_argument("--output", help="결과 폴더 경로")
    parser.add_argument("--dry-run", action="store_true", help="모델 호출과 저장 없이 실행 계획 확인")
    return parser.parse_args(argv)


def validate_matching_definitions(
    existing: list[dict[str, Any]], generated: list[dict[str, Any]],
) -> None:
    existing_pairs = {(str(item["id"]), str(item["name"])) for item in existing}
    generated_pairs = {(str(item["id"]), str(item["name"])) for item in generated}
    if existing_pairs != generated_pairs:
        raise ValueError("AI 생성 정의와 기존 정의의 카테고리 ID·이름 구성이 다릅니다")


def output_path(options: argparse.Namespace) -> Path:
    if options.output:
        return Path(options.output).resolve()
    return RESULTS_ROOT / datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _display_percent(value: Any) -> str:
    return "N/A" if value is None else f"{float(value) * 100:.1f}%"


def write_comparison_report(
    output: Path,
    metrics_rows: list[dict[str, Any]],
    generated_path: Path,
) -> None:
    by_id = {condition.id: condition for condition in CONDITIONS}
    table_rows = []
    for metrics in metrics_rows:
        condition = by_id[str(metrics["scenario"])]
        table_rows.append({
            "condition": condition.id,
            "label": condition.label,
            "threshold": metrics["threshold"],
            "top1Accuracy": metrics["top1Accuracy"],
            "exactAccuracy": metrics["exactAccuracy"],
            "relaxedAccuracy": metrics["relaxedAccuracy"],
            "serviceFinalAccuracy": metrics["serviceRelaxedAccuracy"],
            "fallbackUsageRate": metrics["fallbackUsageRate"],
            "averageDurationMs": metrics["averageTotalDurationMs"],
        })
    write_json(output / "reports" / "comparison.json", table_rows)
    write_csv(output / "reports" / "comparison.csv", table_rows, list(table_rows[0]))
    lines = [
        "# 카테고리 설명 비교", "",
        f"- AI 생성 정의: `{generated_path}`",
        f"- 데이터 수: {metrics_rows[0]['evaluatedCount'] if metrics_rows else 0}",
        f"- 임계값: {metrics_rows[0]['threshold'] if metrics_rows else 'N/A'}", "",
        "| 조건 | Top-1 | 완화 정확도 | fallback 적용 최종 정답률 | fallback 사용 | 평균 시간(ms) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in table_rows:
        lines.append(
            f"| {row['label']} | {_display_percent(row['top1Accuracy'])} | "
            f"{_display_percent(row['relaxedAccuracy'])} | "
            f"{_display_percent(row['serviceFinalAccuracy'])} | "
            f"{_display_percent(row['fallbackUsageRate'])} | "
            f"{float(row['averageDurationMs'] or 0):.1f} |"
        )
    (output / "reports").mkdir(parents=True, exist_ok=True)
    (output / "reports" / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    options = parse_args(argv)
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    threshold = options.threshold if options.threshold is not None else float(config["classification"]["threshold"])
    if not 0 <= threshold <= 1:
        raise ValueError("--threshold는 0 이상 1 이하여야 합니다")

    memo_root = ROOT / "dataset" / "memo"
    category_names = load_categories(memo_root)
    existing_path = ROOT / "config" / "categories.json"
    generated_path = Path(options.generated_definitions).resolve()
    existing = load_category_definitions(existing_path, memo_root)
    generated = load_category_definitions(generated_path, memo_root)
    validate_matching_definitions(existing, generated)
    items = load_memo_dataset(memo_root, category_names)
    if options.limit is not None:
        if options.limit < 1:
            raise ValueError("--limit는 1 이상이어야 합니다")
        items = items[:options.limit]
    expected_calls = len(items) * len(CONDITIONS)
    output = output_path(options)
    print(f"모델: {classification.MODEL}")
    print(f"데이터: {len(items)}개")
    print(f"조건: {len(CONDITIONS)}개")
    print(f"예상 호출: {expected_calls}회")
    print(f"임계값: {threshold:.2f}")
    print(f"출력: {output}")
    if options.dry_run:
        print("[DRY-RUN] 모델을 호출하거나 결과를 저장하지 않았습니다")
        return 0

    client = OllamaClient(
        config["ollamaBaseUrl"], config["connectTimeoutSeconds"], config["readTimeoutSeconds"]
    )
    installed = client.models()
    if not classification.model_installed(classification.MODEL, installed):
        raise ValueError(f"Ollama 모델이 설치되어 있지 않습니다: {classification.MODEL}")
    prompt_template = load_prompt(PROMPT_PATH)
    metrics_rows = []
    for condition_index, condition in enumerate(CONDITIONS, 1):
        definitions = generated if condition.definitions_source == "generated" else existing
        scenario = classification.Scenario(condition.id, "split", condition.include_descriptions, 1)
        raw_records = []
        print(f"[{condition_index}/{len(CONDITIONS)}] {condition.label}")
        for item_index, item in enumerate(items, 1):
            print(f"  [{item_index}/{len(items)}] {item['testId']} {item.get('title', '')}")
            prompt = build_prompt(
                prompt_template, item["input"], category_names,
                title=item.get("title", ""), category_definitions=definitions,
                include_category_descriptions=condition.include_descriptions,
            )
            call = classification.invoke_multi(client, config, prompt, definitions, integrated=False)
            raw_records.append(classification.make_raw_record(scenario, item, 1, call, None, None))
        write_json(output / "raw" / condition.id / "results.json", raw_records)
        _, metrics = classification.evaluate_scenario_threshold(
            output, scenario, raw_records, threshold, definitions, config
        )
        metrics["label"] = condition.label
        metrics["definitionsPath"] = str(generated_path if condition.definitions_source == "generated" else existing_path)
        metrics_rows.append(metrics)
    write_comparison_report(output, metrics_rows, generated_path)
    write_json(output / "run-metadata.json", {
        "model": classification.MODEL,
        "dataCount": len(items),
        "conditions": [condition.__dict__ for condition in CONDITIONS],
        "expectedCallCount": expected_calls,
        "threshold": threshold,
        "generatedDefinitions": str(generated_path),
        "completedAt": datetime.now().astimezone().isoformat(),
    })
    client.unload(classification.MODEL)
    print(f"[OK] 비교 완료: {output / 'reports' / 'comparison.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
