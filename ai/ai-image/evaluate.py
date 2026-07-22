from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any


def levenshtein(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def normalize_text(value: str) -> str:
    return "".join(value.lower().split())


def evaluate_category_evidence(
    truth: dict[str, Any], result: dict[str, Any]
) -> tuple[bool | None, float | None, int, int]:
    concept_groups = truth.get("category_concepts", [])
    if not concept_groups:
        return None, None, 0, 0

    extracted = normalize_text(
        " ".join(
            [
                str(result.get("title", "")),
                str(result.get("description", "")),
                str(result.get("ocr_text", "")),
                *[str(value) for value in result.get("tags", [])],
                *[str(value) for value in result.get("objects", [])],
            ]
        )
    )
    matched = sum(
        any(normalize_text(str(alias)) in extracted for alias in aliases)
        for aliases in concept_groups
    )
    total = len(concept_groups)
    minimum = int(truth.get("min_category_concepts", total))
    return matched >= minimum, matched / total, matched, total


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * ratio) - 1)
    return ordered[index]


def load_results(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def calculate_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        raise ValueError("평가할 결과가 없습니다.")

    successes = [record for record in records if record.get("error") is None]
    latencies = [
        float(record["latency_ms"])
        for record in successes
        if record.get("latency_ms") is not None
    ]

    category_scores: list[bool] = []
    cer_scores: list[float] = []
    tag_recalls: list[float] = []
    category_evidence_scores: list[float] = []
    category_readiness_scores: list[bool] = []
    expected_by_category: dict[str, set[str]] = {}
    predicted_by_category: dict[str, set[str]] = {}

    for record in successes:
        truth = record.get("ground_truth", {})
        result = record.get("result") or {}

        expected_category = truth.get("category")
        predicted_category = result.get("category")
        if expected_category and predicted_category:
            category_scores.append(result.get("category") == expected_category)
            sample_id = str(record.get("sample_id", ""))
            expected_by_category.setdefault(expected_category, set()).add(sample_id)
            predicted_by_category.setdefault(predicted_category, set()).add(sample_id)

        expected_ocr = normalize_text(str(truth.get("ocr_text", "")))
        if expected_ocr:
            predicted_ocr = normalize_text(str(result.get("ocr_text", "")))
            cer_scores.append(
                levenshtein(expected_ocr, predicted_ocr) / max(1, len(expected_ocr))
            )

        required_tags = {str(tag).lower() for tag in truth.get("required_tags", [])}
        if required_tags:
            predicted_tags = {str(tag).lower() for tag in result.get("tags", [])}
            tag_recalls.append(len(required_tags & predicted_tags) / len(required_tags))

    # Pipeline 기준 평가는 실패 응답도 0점으로 포함합니다. 성공 응답만 분모에
    # 넣으면 JSON이 잘린 모델의 분류 준비도가 과대평가됩니다.
    for record in records:
        truth = record.get("ground_truth", {})
        result = record.get("result") or {}
        ready, evidence_score, _, _ = evaluate_category_evidence(truth, result)
        if ready is not None and evidence_score is not None:
            category_readiness_scores.append(ready)
            category_evidence_scores.append(evidence_score)

    category_search: dict[str, dict[str, float | int]] = {}
    categories = sorted(expected_by_category.keys() | predicted_by_category.keys())
    for category in categories:
        expected_ids = expected_by_category.get(category, set())
        predicted_ids = predicted_by_category.get(category, set())
        true_positives = len(expected_ids & predicted_ids)
        precision = true_positives / len(predicted_ids) if predicted_ids else 0.0
        recall = true_positives / len(expected_ids) if expected_ids else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall > 0
            else 0.0
        )
        category_search[category] = {
            "expected_count": len(expected_ids),
            "returned_count": len(predicted_ids),
            "true_positives": true_positives,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    search_values = list(category_search.values())
    return {
        "sample_count": len(records),
        "success_count": len(successes),
        "success_rate": len(successes) / len(records),
        "json_valid_rate": (
            sum(bool(record.get("json_valid")) for record in records) / len(records)
        ),
        "avg_latency_ms": mean(latencies) if latencies else None,
        "p95_latency_ms": percentile(latencies, 0.95) if latencies else None,
        "category_accuracy": mean(category_scores) if category_scores else None,
        "search_macro_precision": (
            mean(float(item["precision"]) for item in search_values)
            if search_values
            else None
        ),
        "search_macro_recall": (
            mean(float(item["recall"]) for item in search_values)
            if search_values
            else None
        ),
        "search_macro_f1": (
            mean(float(item["f1"]) for item in search_values)
            if search_values
            else None
        ),
        "category_search": category_search,
        "ocr_cer": mean(cer_scores) if cer_scores else None,
        "tag_recall": mean(tag_recalls) if tag_recalls else None,
        "category_evidence_recall": (
            mean(category_evidence_scores) if category_evidence_scores else None
        ),
        "category_readiness_rate": (
            mean(category_readiness_scores) if category_readiness_scores else None
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="이미지 모델 결과 평가")
    parser.add_argument("--result", type=Path, required=True, help="결과 JSONL 경로")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = load_results(args.result)
    if not records:
        raise ValueError("결과 파일이 비어 있습니다.")

    metrics = calculate_metrics(records)

    def percent(score: float) -> str:
        return f"{score * 100:.2f}%"

    print(f"전체 샘플: {metrics['sample_count']}")
    print(f"성공률: {percent(metrics['success_rate'])}")
    print(f"JSON 파싱 성공률: {percent(metrics['json_valid_rate'])}")
    if metrics["avg_latency_ms"] is not None:
        print(f"평균 처리 시간: {metrics['avg_latency_ms']:.2f} ms")
        print(f"P95 처리 시간: {metrics['p95_latency_ms']:.2f} ms")
    if metrics["category_accuracy"] is not None:
        print(f"카테고리 정확도: {percent(metrics['category_accuracy'])}")
    if metrics["search_macro_f1"] is not None:
        print(
            "카테고리 검색 Macro P/R/F1: "
            f"{percent(metrics['search_macro_precision'])} / "
            f"{percent(metrics['search_macro_recall'])} / "
            f"{percent(metrics['search_macro_f1'])}"
        )
    if metrics["ocr_cer"] is not None:
        print(f"OCR CER(낮을수록 좋음): {percent(metrics['ocr_cer'])}")
    if metrics["tag_recall"] is not None:
        print(f"필수 태그 재현율: {percent(metrics['tag_recall'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
