import pytest

from src.relaxed_evaluator import (
    RelaxedEvaluationStatus as Status,
    evaluate_single_gold_relaxed,
    strict_multi_label_metrics,
    summarize_threshold_rows,
)


@pytest.mark.parametrize(("predicted", "invalid", "expected"), [
    (["GOLD"], [], Status.EXACT_CORRECT),
    (["GOLD", "EXTRA"], [], Status.RELAXED_CORRECT),
    (["GOLD", "EXTRA", "THIRD"], [], Status.WRONG_OVER_PREDICTION),
    (["EXTRA"], [], Status.WRONG_MISSING_GOLD),
    (["EXTRA", "THIRD"], [], Status.WRONG_MISSING_GOLD),
    ([], [], Status.EMPTY_PREDICTION),
    (["GOLD"], [{"errorType": "INVALID_CATEGORY"}], Status.INVALID_PREDICTION),
])
def test_single_gold_relaxed_statuses(predicted, invalid, expected):
    assert evaluate_single_gold_relaxed("GOLD", predicted, invalid) == expected


def test_duplicate_predictions_are_removed_before_evaluation():
    assert evaluate_single_gold_relaxed("GOLD", ["GOLD", "GOLD", "EXTRA"]) == Status.RELAXED_CORRECT


def test_strict_metrics_treat_extra_category_as_false_positive():
    rows = [{
        "expectedCategoryId": "GOLD", "thresholdSelectedCategoryIds": ["GOLD", "EXTRA"],
        "top1Correct": True, "exactCorrect": False, "relaxedCorrect": True,
        "goldIncluded": True, "overPrediction": False, "missingGold": False,
        "selectedCategoryCount": 2, "extraCategoryCount": 1,
        "hasInvalidPrediction": False, "fallbackUsed": False, "thresholdMiss": False,
        "evaluationStatus": "RELAXED_CORRECT",
    }]
    metrics = summarize_threshold_rows(rows, ["GOLD", "EXTRA"])
    assert metrics["relaxedAccuracy"] == 1
    assert metrics["exactAccuracy"] == 0
    assert metrics["strictMicroPrecision"] == pytest.approx(0.5)
    assert metrics["strictMicroRecall"] == 1
    assert metrics["hammingLoss"] == pytest.approx(0.5)
    assert metrics["jaccardScore"] == pytest.approx(0.5)
