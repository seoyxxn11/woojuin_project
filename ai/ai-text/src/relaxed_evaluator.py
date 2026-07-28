from __future__ import annotations

from collections import Counter
from enum import Enum
from typing import Any


class RelaxedEvaluationStatus(str, Enum):
    EXACT_CORRECT = "EXACT_CORRECT"
    RELAXED_CORRECT = "RELAXED_CORRECT"
    WRONG_MISSING_GOLD = "WRONG_MISSING_GOLD"
    WRONG_OVER_PREDICTION = "WRONG_OVER_PREDICTION"
    INVALID_PREDICTION = "INVALID_PREDICTION"
    EMPTY_PREDICTION = "EMPTY_PREDICTION"
    FALLBACK_USED = "FALLBACK_USED"


def evaluate_single_gold_relaxed(
    gold_category_id: str,
    predicted_category_ids: list[str],
    invalid_predictions: list[Any] | None = None,
    max_allowed_extra_categories: int = 1,
) -> RelaxedEvaluationStatus:
    predictions = set(predicted_category_ids)
    if invalid_predictions:
        return RelaxedEvaluationStatus.INVALID_PREDICTION
    if not predictions:
        return RelaxedEvaluationStatus.EMPTY_PREDICTION
    if gold_category_id not in predictions:
        return RelaxedEvaluationStatus.WRONG_MISSING_GOLD
    extra_count = len(predictions - {gold_category_id})
    if extra_count == 0:
        return RelaxedEvaluationStatus.EXACT_CORRECT
    if extra_count <= max_allowed_extra_categories:
        return RelaxedEvaluationStatus.RELAXED_CORRECT
    return RelaxedEvaluationStatus.WRONG_OVER_PREDICTION


def strict_multi_label_metrics(rows: list[dict[str, Any]], category_ids: list[str]) -> dict[str, Any]:
    if not rows:
        return _empty_strict_metrics()
    labels = set(category_ids)
    per_label: dict[str, dict[str, float | int | None]] = {}
    total_tp = total_fp = total_fn = 0
    hamming_errors = 0
    jaccards: list[float] = []
    for category_id in category_ids:
        tp = fp = fn = support = 0
        for row in rows:
            gold = {str(row["expectedCategoryId"])}
            predicted = set(row.get("thresholdSelectedCategoryIds", [])) & labels
            support += category_id in gold
            tp += category_id in gold and category_id in predicted
            fp += category_id not in gold and category_id in predicted
            fn += category_id in gold and category_id not in predicted
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_label[category_id] = {
            "support": support, "precision": precision, "recall": recall, "f1": f1,
        }
        total_tp += tp
        total_fp += fp
        total_fn += fn
    for row in rows:
        gold = {str(row["expectedCategoryId"])}
        predicted = set(row.get("thresholdSelectedCategoryIds", [])) & labels
        hamming_errors += len(gold.symmetric_difference(predicted))
        union = gold | predicted
        jaccards.append(len(gold & predicted) / len(union) if union else 1.0)
    micro_precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 0.0
    micro_recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 0.0
    micro_f1 = (
        2 * micro_precision * micro_recall / (micro_precision + micro_recall)
        if micro_precision + micro_recall else 0.0
    )
    macro_precision = sum(float(item["precision"] or 0) for item in per_label.values()) / len(category_ids)
    macro_recall = sum(float(item["recall"] or 0) for item in per_label.values()) / len(category_ids)
    macro_f1 = sum(float(item["f1"] or 0) for item in per_label.values()) / len(category_ids)
    support_total = sum(int(item["support"] or 0) for item in per_label.values())
    weighted_f1 = (
        sum(float(item["f1"] or 0) * int(item["support"] or 0) for item in per_label.values())
        / support_total if support_total else 0.0
    )
    return {
        "strictMicroPrecision": micro_precision,
        "strictMicroRecall": micro_recall,
        "strictMicroF1": micro_f1,
        "strictMacroPrecision": macro_precision,
        "strictMacroRecall": macro_recall,
        "strictMacroF1": macro_f1,
        "weightedF1": weighted_f1,
        "hammingLoss": hamming_errors / (len(rows) * len(category_ids)),
        "jaccardScore": sum(jaccards) / len(jaccards),
        "perCategory": per_label,
    }


def summarize_threshold_rows(rows: list[dict[str, Any]], category_ids: list[str]) -> dict[str, Any]:
    count = len(rows)
    statuses = Counter(str(row.get("evaluationStatus", "")) for row in rows)
    rate = lambda key: sum(bool(row.get(key)) for row in rows) / count if count else None
    average = lambda key: sum(float(row.get(key, 0) or 0) for row in rows) / count if count else None
    strict = strict_multi_label_metrics(rows, category_ids)
    return {
        "evaluatedCount": count,
        "top1Accuracy": rate("top1Correct"),
        "rawGoldPresenceRate": rate("rawGoldPresent"),
        "exactAccuracy": rate("exactCorrect"),
        "relaxedAccuracy": rate("relaxedCorrect"),
        "goldCoverage": rate("goldIncluded"),
        "overPredictionRate": rate("overPrediction"),
        "missingGoldRate": rate("missingGold"),
        "averageSelectedCategoryCount": average("selectedCategoryCount"),
        "averageExtraCategoryCount": average("extraCategoryCount"),
        "invalidPredictionRate": rate("hasInvalidPrediction"),
        "fallbackUsageRate": rate("fallbackUsed"),
        "serviceGoldCoverage": rate("serviceGoldIncluded"),
        "serviceExactAccuracy": rate("serviceExactCorrect"),
        "serviceRelaxedAccuracy": rate("serviceRelaxedCorrect"),
        "thresholdMissRate": rate("thresholdMiss"),
        "statusDistribution": {
            status.value: {
                "count": statuses.get(status.value, 0),
                "rate": statuses.get(status.value, 0) / count if count else None,
            }
            for status in RelaxedEvaluationStatus
            if status is not RelaxedEvaluationStatus.FALLBACK_USED
        },
        **strict,
    }


def _empty_strict_metrics() -> dict[str, Any]:
    return {
        "strictMicroPrecision": None, "strictMicroRecall": None, "strictMicroF1": None,
        "strictMacroPrecision": None, "strictMacroRecall": None, "strictMacroF1": None,
        "weightedF1": None, "hammingLoss": None, "jaccardScore": None,
        "perCategory": {},
    }
