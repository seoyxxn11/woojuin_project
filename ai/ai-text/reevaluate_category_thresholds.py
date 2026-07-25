from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from main import write_classification_outputs
from run_classification_experiment import evaluate_raw_record
from src.multi_label_selector import category_maps
from src.result_writer import write_csv, write_json


ROOT = Path(__file__).resolve().parent
DEFAULT_THRESHOLDS = (0.55, 0.60, 0.65, 0.70, 0.75)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="저장된 category-only 결과를 여러 임계값으로 다시 평가합니다.",
    )
    parser.add_argument(
        "--result-dir",
        required=True,
        type=Path,
        help="classification-results.json이 있는 기존 실행 결과 폴더",
    )
    parser.add_argument(
        "--thresholds",
        nargs="+",
        type=float,
        default=list(DEFAULT_THRESHOLDS),
        help="비교할 임계값 목록 (기본: 0.55 0.60 0.65 0.70 0.75)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="출력 폴더 (기본: <result-dir>/threshold-comparison)",
    )
    return parser.parse_args(argv)


def validate_thresholds(values: list[float]) -> list[float]:
    thresholds = sorted(set(values))
    if not thresholds or any(value < 0 or value > 1 for value in thresholds):
        raise ValueError("임계값은 0 이상 1 이하의 숫자여야 합니다.")
    return thresholds


def load_json(path: Path) -> Any:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def reevaluate_row(
    row: dict[str, Any],
    threshold: float,
    definitions: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    evaluation = evaluate_raw_record(
        row,
        threshold,
        definitions,
        config["classification"],
        config["evaluation"],
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
        if evaluation.get("top1CategoryId") in by_id
        else ""
    )
    evaluation["inputType"] = row.get("inputType", "")
    evaluation["expectedCategory"] = row.get(
        "expectedCategory",
        evaluation["expectedCategoryName"],
    )
    evaluation["modelId"] = row.get("modelId", row.get("model", ""))
    evaluation["provider"] = row.get("provider", "")
    evaluation["requestedModel"] = row.get("requestedModel", "")
    evaluation["status"] = row.get("status", "")
    evaluation["errorType"] = row.get("errorType", "")
    evaluation["errorMessage"] = row.get("errorMessage", "")
    evaluation["executedAt"] = row.get("executedAt")
    return evaluation


def main(argv: list[str] | None = None) -> int:
    options = parse_args(argv)
    result_dir = options.result_dir.resolve()
    rows_path = result_dir / "classification-results.json"
    definitions_path = result_dir / "category-descriptions.json"
    metadata_path = result_dir / "run-metadata.json"
    for path in (rows_path, definitions_path, metadata_path):
        if not path.is_file():
            raise FileNotFoundError(f"필수 결과 파일이 없습니다: {path}")

    thresholds = validate_thresholds(options.thresholds)
    rows = load_json(rows_path)
    definitions = load_json(definitions_path)
    metadata = load_json(metadata_path)
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    categories = [str(item["name"]) for item in definitions]
    output = (options.output or result_dir / "threshold-comparison").resolve()

    comparison: list[dict[str, Any]] = []
    for threshold in thresholds:
        threshold_rows = [
            reevaluate_row(row, threshold, definitions, config)
            for row in rows
        ]
        threshold_metadata = deepcopy(metadata)
        threshold_metadata.setdefault("options", {})["threshold"] = threshold
        threshold_metadata["sourceResultDirectory"] = str(result_dir)
        threshold_dir = output / f"{threshold:.2f}"
        write_classification_outputs(
            threshold_dir,
            threshold_metadata,
            threshold_rows,
            categories,
            definitions,
        )
        summary = load_json(threshold_dir / "classification-summary.json")[0]
        comparison.append({"threshold": threshold, **summary})

    fields = [
        "threshold",
        "count",
        "correctCount",
        "top1Accuracy",
        "exactAccuracy",
        "relaxedAccuracy",
        "averageSelectedCategoryCount",
        "macroPrecision",
        "macroRecall",
        "macroF1",
    ]
    write_json(output / "threshold-comparison.json", comparison)
    write_csv(output / "threshold-comparison.csv", comparison, fields)

    lines = [
        "# 카테고리 임계값 비교",
        "",
        f"- 원본 결과: {result_dir}",
        "- 모델 재호출: 없음",
        "",
        "| 임계값 | 데이터 수 | 정답 포함 수 | Top-1 | 정확 일치 | 완화 정확도 | 평균 선택 수 | Macro F1 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in comparison:
        percent = lambda key: f"{float(item[key]) * 100:.1f}%"
        lines.append(
            f"| {item['threshold']:.2f} | {item['count']} | {item['correctCount']} | "
            f"{percent('top1Accuracy')} | {percent('exactAccuracy')} | "
            f"{percent('relaxedAccuracy')} | "
            f"{float(item['averageSelectedCategoryCount']):.3f} | "
            f"{percent('macroF1')} |"
        )
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[OK] 임계값: {', '.join(f'{value:.2f}' for value in thresholds)}")
    print(f"[OK] 결과: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
