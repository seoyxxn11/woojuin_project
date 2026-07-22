from __future__ import annotations
from collections import defaultdict
import math
import statistics
from typing import Any

def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    low, high = math.floor(index), math.ceil(index)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)

def average(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None

def rate(values: list[bool]) -> float | None:
    return sum(values) / len(values) if values else None

def classification_metrics(rows: list[dict], categories: list[str]) -> dict[str, Any]:
    eligible = [row for row in rows if row.get("expectedCategory") in categories]
    usable = [row for row in eligible if row.get("generatedCategory") in categories]
    matrix = {actual: {predicted: 0 for predicted in categories} for actual in categories}
    for row in usable:
        matrix[row["expectedCategory"]][row["generatedCategory"]] += 1
    per_category: dict[str, dict[str, Any]] = {}
    for category in categories:
        tp = matrix[category][category]
        fp = sum(matrix[actual][category] for actual in categories if actual != category)
        fn = sum(matrix[category][predicted] for predicted in categories if predicted != category)
        support = sum(row.get("expectedCategory") == category for row in eligible)
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else (0.0 if precision is not None and recall is not None else None)
        per_category[category] = {"support": support, "precision": precision, "recall": recall, "f1": f1}
    precision_values = [x["precision"] for x in per_category.values() if x["precision"] is not None]
    recall_values = [x["recall"] for x in per_category.values() if x["recall"] is not None]
    f1_values = [x["f1"] for x in per_category.values() if x["f1"] is not None]
    accuracy = sum(matrix[c][c] for c in categories) / len(eligible) if eligible else None
    confusions = sorted(
        (
            {"actual": actual, "predicted": predicted, "count": count}
            for actual in categories for predicted, count in matrix[actual].items()
            if actual != predicted and count
        ),
        key=lambda item: item["count"], reverse=True,
    )
    return {
        "evaluatedCount": len(eligible),
        "invalidPredictionCount": len(eligible) - len(usable),
        "accuracy": accuracy,
        "macroPrecision": average(precision_values),
        "macroRecall": average(recall_values),
        "macroF1": average(f1_values),
        "perCategory": per_category,
        "confusionMatrix": matrix,
        "majorConfusions": confusions,
    }

def confidence_metrics(rows: list[dict]) -> dict[str, Any]:
    usable = [row for row in rows if isinstance(row.get("confidence"), (int, float)) and not isinstance(row.get("confidence"), bool)]
    correct = [float(row["confidence"]) for row in usable if row.get("categoryCorrect") is True]
    incorrect = [float(row["confidence"]) for row in usable if row.get("categoryCorrect") is False]
    buckets = []
    for low, high in ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)):
        selected = [row for row in usable if low <= float(row["confidence"]) <= high] if high == 1.0 else [row for row in usable if low <= float(row["confidence"]) < high]
        buckets.append({"range": f"{low:.1f}-{high:.1f}", "count": len(selected), "accuracy": rate([row.get("categoryCorrect") is True for row in selected])})
    return {
        "averageConfidence": average([float(row["confidence"]) for row in usable]),
        "averageConfidenceCorrect": average(correct),
        "averageConfidenceIncorrect": average(incorrect),
        "buckets": buckets,
    }

def operational_metrics(rows: list[dict]) -> dict[str, Any]:
    successful = [row for row in rows if not row.get("requestFailed")]
    durations = [float(row["totalDurationMs"]) for row in successful if row.get("totalDurationMs") not in (None, "")]
    load_durations = [float(row["loadDurationMs"]) for row in successful if row.get("loadDurationMs") not in (None, "")]
    generation_durations = [float(row["evalDurationMs"]) for row in successful if row.get("evalDurationMs") not in (None, "")]
    return {
        "averageResponseTimeMs": average(durations),
        "medianResponseTimeMs": statistics.median(durations) if durations else None,
        "p95ResponseTimeMs": percentile(durations, 0.95),
        "minResponseTimeMs": min(durations) if durations else None,
        "maxResponseTimeMs": max(durations) if durations else None,
        "averageTokensPerSecond": average([float(row["tokensPerSecond"]) for row in successful if row.get("tokensPerSecond") not in (None, "")]),
        "averagePromptTokens": average([float(row["promptEvalCount"]) for row in successful if row.get("promptEvalCount") not in (None, "")]),
        "averageOutputTokens": average([float(row["evalCount"]) for row in successful if row.get("evalCount") not in (None, "")]),
        "averageLoadDurationMs": average(load_durations),
        "averageGenerationDurationMs": average(generation_durations),
    }

def nullable_average(rows: list[dict], key: str) -> float | None:
    values = [float(row[key]) for row in rows if row.get(key) not in (None, "")]
    return average(values)

def nullable_rate(rows: list[dict], key: str) -> float | None:
    values = [row[key] is True for row in rows if row.get(key) is not None]
    return rate(values)
