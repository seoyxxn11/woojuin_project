from __future__ import annotations

from typing import Any


def category_maps(definitions: list[dict[str, Any]]) -> tuple[dict[str, dict], dict[str, dict]]:
    by_id: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    for definition in definitions:
        category_id = str(definition.get("id", "")).strip()
        category_name = str(definition.get("name", "")).strip()
        if not category_id or not category_name:
            raise ValueError("각 카테고리 정의에는 id와 name이 필요합니다")
        if category_id in by_id or category_name in by_name:
            raise ValueError("카테고리 id 또는 name이 중복되었습니다")
        by_id[category_id] = definition
        by_name[category_name] = definition
    return by_id, by_name


def resolve_category_id(value: str, definitions: list[dict[str, Any]]) -> str:
    by_id, by_name = category_maps(definitions)
    if value in by_id:
        return value
    if value in by_name:
        return str(by_name[value]["id"])
    raise ValueError(f"존재하지 않는 카테고리: {value}")


def select_categories(
    valid_predictions: list[dict[str, Any]],
    *,
    threshold: float,
    ensure_at_least_one: bool,
    fallback_category_id: str,
    service_max_categories: int,
) -> dict[str, Any]:
    if not 0 <= threshold <= 1:
        raise ValueError("threshold는 0 이상 1 이하여야 합니다")
    if service_max_categories < 1:
        raise ValueError("service_max_categories는 1 이상이어야 합니다")

    ordered = sorted(valid_predictions, key=lambda item: float(item["score"]), reverse=True)
    selected = [item for item in ordered if float(item["score"]) >= threshold]
    ensure_used = False
    if not selected and ordered and ensure_at_least_one:
        selected = [ordered[0]]
        ensure_used = True

    threshold_ids = [str(item["categoryId"]) for item in selected]
    fallback_used = not ordered
    service_ids = threshold_ids[:service_max_categories]
    if fallback_used:
        service_ids = [fallback_category_id]

    return {
        "threshold": threshold,
        "thresholdSelectedCategoryIds": threshold_ids,
        "serviceSelectedCategoryIds": service_ids,
        "ensureAtLeastOneUsed": ensure_used,
        "fallbackUsed": fallback_used,
        "serviceLimitApplied": len(threshold_ids) > service_max_categories,
    }
