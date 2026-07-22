from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from evaluate import calculate_metrics, evaluate_category_evidence, load_results
from search import write_search_index


ROOT = Path(__file__).resolve().parent


def percent(value: float | None) -> str:
    return "-" if value is None else f"{value * 100:.2f}%"


def milliseconds(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def seconds(value: float | None) -> str:
    return "-" if value is None else f"{value / 1000:.2f}초"


def accuracy_from_error_rate(value: float | None) -> float | None:
    return None if value is None else max(0.0, 1.0 - value)


def category_score(run: dict[str, Any]) -> str:
    comparable = [
        record
        for record in run["records"]
        if record.get("ground_truth", {}).get("category")
        and (record.get("result") or {}).get("category")
    ]
    correct = sum(
        record["ground_truth"]["category"] == record["result"]["category"]
        for record in comparable
    )
    return f"{correct}/{len(comparable)}" if comparable else "-"


def escape_markdown(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def discover_runs(results_dir: Path) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for result_path in sorted(results_dir.glob("*.jsonl")):
        if result_path.stat().st_size == 0:
            continue
        try:
            records = load_results(result_path)
        except (json.JSONDecodeError, OSError):
            continue
        if not records:
            continue

        first_record = records[0]
        provider = first_record.get("provider", "unknown")
        # GMS 연결·설정 확인 과정에서 전부 실패한 실행은 모델 성능 비교가
        # 아니므로 누적 보고서에서 제외합니다. 원본 JSONL은 진단용으로 보존합니다.
        if provider in {"gms", "gemini_gms"} and not any(
            record.get("error") is None for record in records
        ):
            continue

        metrics = calculate_metrics(records)
        runs.append(
            {
                "run": result_path.stem,
                "file": result_path.name,
                "model": first_record.get("model", "unknown"),
                "provider": provider,
                "metrics": metrics,
                "records": records,
            }
        )
    return runs


def write_summary_csv(runs: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "run",
        "model",
        "provider",
        "sample_count",
        "success_rate",
        "json_valid_rate",
        "category_accuracy",
        "search_macro_precision",
        "search_macro_recall",
        "search_macro_f1",
        "ocr_cer",
        "tag_recall",
        "category_evidence_recall",
        "category_readiness_rate",
        "avg_latency_ms",
        "p95_latency_ms",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for run in runs:
            metrics = run["metrics"]
            writer.writerow(
                {
                    "run": run["run"],
                    "model": run["model"],
                    "provider": run["provider"],
                    **{field: metrics.get(field) for field in fields if field in metrics},
                }
            )


def write_samples_csv(runs: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "run",
        "model",
        "sample_id",
        "expected_category",
        "predicted_category",
        "category_correct",
        "expected_ocr",
        "predicted_ocr",
        "expected_tags",
        "predicted_tags",
        "target_category",
        "category_evidence_ready",
        "category_evidence_recall",
        "latency_ms",
        "json_valid",
        "error",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for run in runs:
            for record in run["records"]:
                truth = record.get("ground_truth", {})
                result = record.get("result") or {}
                expected_category = truth.get("category", "")
                predicted_category = result.get("category", "")
                ready, evidence_recall, _, _ = evaluate_category_evidence(truth, result)
                writer.writerow(
                    {
                        "run": run["run"],
                        "model": run["model"],
                        "sample_id": record.get("sample_id", ""),
                        "expected_category": expected_category,
                        "predicted_category": predicted_category,
                        "category_correct": (
                            expected_category == predicted_category
                            if expected_category
                            else ""
                        ),
                        "expected_ocr": truth.get("ocr_text", ""),
                        "predicted_ocr": result.get("ocr_text", ""),
                        "expected_tags": ", ".join(truth.get("required_tags", [])),
                        "predicted_tags": ", ".join(result.get("tags", [])),
                        "target_category": truth.get("target_category", ""),
                        "category_evidence_ready": ready if ready is not None else "",
                        "category_evidence_recall": (
                            evidence_recall if evidence_recall is not None else ""
                        ),
                        "latency_ms": record.get("latency_ms", ""),
                        "json_valid": record.get("json_valid", False),
                        "error": record.get("error") or "",
                    }
                )


def write_markdown(runs: list[dict[str, Any]], path: Path) -> None:
    lines = [
        "# 이미지 모델 비교 보고서",
        "",
        f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 비교 실행 수: {len(runs)}",
        "",
        "## 한눈에 보는 결과",
        "",
        "| 모델 및 실행 | 테스트 이미지 | 실행 성공률 | OCR 인식 정확도 | 태그 일치율 | 분류 근거 충족률 | 근거 개념 재현율 | 이미지당 평균 시간 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    if not runs:
        lines.append("| 결과 없음 | - | - | - | - | - | - | - |")
    else:
        for run in runs:
            metrics = run["metrics"]
            lines.append(
                "| **{model}**<br><sub>{run}</sub> | {count}장 | {success} | "
                "{ocr} | {tags} | {readiness} | {evidence} | {average} |".format(
                    run=escape_markdown(run["run"]),
                    model=escape_markdown(run["model"]),
                    count=metrics["sample_count"],
                    success=percent(metrics["success_rate"]),
                    ocr=percent(accuracy_from_error_rate(metrics["ocr_cer"])),
                    tags=percent(metrics["tag_recall"]),
                    readiness=percent(metrics["category_readiness_rate"]),
                    evidence=percent(metrics["category_evidence_recall"]),
                    average=seconds(metrics["avg_latency_ms"]),
                )
            )

    lines.extend(
        [
            "",
            "> **읽는 법:** 분류 근거 충족률은 이미지 모델이 최종 카테고리 선택에 필요한 서로 다른 근거 개념을 최소 개수 이상 추출한 비율입니다.",
            "> OCR 인식 정확도는 `100% - 문자 오류율(CER)`로 표시했습니다. 모든 정확도는 높을수록 좋습니다.",
            "",
            "## 해석 및 주의사항",
            "",
        ]
    )

    successful_runs = [run for run in runs if run["metrics"]["success_rate"] > 0]
    failed_runs = [run for run in runs if run["metrics"]["success_rate"] == 0]
    if successful_runs:
        most_representative = max(
            successful_runs, key=lambda run: run["metrics"]["sample_count"]
        )
        metrics = most_representative["metrics"]
        lines.append(
            "- 현재 가장 많은 이미지로 실행한 **{model}** 결과는 분류 정확도 **{category}**, "
            "태그 일치율 **{tags}**, 검색 F1 **{f1}**입니다.".format(
                model=escape_markdown(most_representative["model"]),
                category=percent(metrics["category_accuracy"]),
                tags=percent(metrics["tag_recall"]),
                f1=percent(metrics["search_macro_f1"]),
            )
        )
    if failed_runs:
        failed_models = ", ".join(f"**{run['model']}**" for run in failed_runs)
        lines.append(f"- {failed_models} 실행은 실패하여 정확도를 계산할 수 없습니다.")
    lines.extend(
        [
            "- 테스트 이미지 수가 다른 실행끼리는 정확도를 직접 비교하면 안 됩니다.",
            "- 5장은 동작 확인용 표본입니다. 모델 선정 전에는 동일한 이미지 30장 이상으로 다시 비교하는 것이 좋습니다.",
        ]
    )

    for run in runs:
        lines.extend(
            [
                "",
                f"## {escape_markdown(run['run'])}",
                "",
                f"- 모델: `{run['model']}`",
                f"- 원본 결과: `results/{run['file']}`",
                "",
                "| 이미지 | 정답 카테고리 | 예측 카테고리 | 판정 | 처리 시간 | 오류 |",
                "| --- | --- | --- | ---: | ---: | --- |",
            ]
        )
        for record in run["records"]:
            truth = record.get("ground_truth", {})
            result = record.get("result") or {}
            lines.append(
                "| {sample} | {expected} | {predicted} | {valid} | {latency} | {error} |".format(
                    sample=escape_markdown(record.get("sample_id", "")),
                    expected=escape_markdown(truth.get("category", "")),
                    predicted=escape_markdown(result.get("category", "")),
                    valid=(
                        "➖ 분류 제외"
                        if not result.get("category") and record.get("json_valid")
                        else
                        "✅ 정답"
                        if truth.get("category") == result.get("category")
                        else "❌ 오답" if record.get("json_valid") else "⚠️ 실행 실패"
                    ),
                    latency=seconds(record.get("latency_ms")),
                    error=escape_markdown(record.get("error") or ""),
                )
            )

        lines.extend(
            [
                "",
                "### 카테고리 검색 평가",
                "",
                "| 검색 카테고리 | 정답 이미지 수 | 반환 이미지 수 | 정확히 반환 | Precision | Recall | F1 |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for category, values in run["metrics"]["category_search"].items():
            lines.append(
                "| {category} | {expected} | {returned} | {correct} | {precision} | {recall} | {f1} |".format(
                    category=category,
                    expected=values["expected_count"],
                    returned=values["returned_count"],
                    correct=values["true_positives"],
                    precision=percent(float(values["precision"])),
                    recall=percent(float(values["recall"])),
                    f1=percent(float(values["f1"])),
                )
            )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_reports(results_dir: Path, reports_dir: Path) -> list[Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    runs = discover_runs(results_dir)
    summary_path = reports_dir / "model-comparison.md"
    summary_csv_path = reports_dir / "model-summary.csv"
    samples_csv_path = reports_dir / "sample-details.csv"
    indexes_dir = reports_dir / "search-indexes"
    indexes_dir.mkdir(parents=True, exist_ok=True)

    active_run_names = {run["run"] for run in runs}
    for stale_index in indexes_dir.glob("*.json"):
        if stale_index.stem not in active_run_names:
            stale_index.unlink()

    write_markdown(runs, summary_path)
    write_summary_csv(runs, summary_csv_path)
    write_samples_csv(runs, samples_csv_path)
    index_paths: list[Path] = []
    for run in runs:
        index_path = indexes_dir / f"{run['run']}.json"
        write_search_index(run["records"], index_path)
        index_paths.append(index_path)
    return [summary_path, summary_csv_path, samples_csv_path, *index_paths]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="누적 이미지 모델 비교 보고서 생성")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = generate_reports(args.results_dir, args.reports_dir)
    for path in paths:
        print(f"보고서 생성: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
