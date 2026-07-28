from src.multi_label_selector import select_categories


def p(category_id, score):
    return {"categoryId": category_id, "categoryName": category_id, "score": score}


def select(predictions, **overrides):
    options = {
        "threshold": 0.7, "ensure_at_least_one": True,
        "fallback_category_id": "OTHER", "service_max_categories": 2,
    } | overrides
    return select_categories(predictions, **options)


def test_score_equal_to_threshold_is_selected():
    assert select([p("A", 0.7)])["thresholdSelectedCategoryIds"] == ["A"]


def test_ensure_at_least_one_selects_highest_valid_candidate():
    result = select([p("A", 0.6), p("B", 0.5)])
    assert result["thresholdSelectedCategoryIds"] == ["A"]
    assert result["ensureAtLeastOneUsed"]


def test_no_valid_candidate_uses_fallback_only_for_service_result():
    result = select([])
    assert result["thresholdSelectedCategoryIds"] == []
    assert result["serviceSelectedCategoryIds"] == ["OTHER"]
    assert result["fallbackUsed"]


def test_service_limit_is_applied_after_full_threshold_selection():
    result = select([p("A", 0.9), p("B", 0.8), p("C", 0.7)])
    assert result["thresholdSelectedCategoryIds"] == ["A", "B", "C"]
    assert result["serviceSelectedCategoryIds"] == ["A", "B"]
    assert result["serviceLimitApplied"]


def test_ensure_disabled_leaves_threshold_result_empty_without_fallback_when_valid_raw_exists():
    result = select([p("A", 0.6)], ensure_at_least_one=False)
    assert result["thresholdSelectedCategoryIds"] == []
    assert result["serviceSelectedCategoryIds"] == []
    assert result["fallbackUsed"] is False
