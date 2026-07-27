from __future__ import annotations

import json
from typing import Any

from src.url_summary_policy import usable_url_summary


DESCRIPTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "description": {"type": "string", "minLength": 1},
        "examples": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {"type": "string", "minLength": 1},
        },
    },
    "required": ["description", "examples"],
}


def select_category_samples(
    items: list[dict[str, Any]],
    category_name: str,
    *,
    max_items: int,
    max_chars_per_item: int,
) -> list[dict[str, str]]:
    if max_items < 1:
        raise ValueError("max_items는 1 이상이어야 합니다")
    if max_chars_per_item < 1:
        raise ValueError("max_chars_per_item은 1 이상이어야 합니다")
    selected = []
    for item in items:
        if item.get("expected", {}).get("categories") != [category_name]:
            continue
        sample = {
            "testId": str(item.get("testId", "")),
            "title": str(item.get("title", "")).strip(),
            "input": str(item.get("input", "")).strip()[:max_chars_per_item],
        }
        if item.get("inputType"):
            sample["inputType"] = str(item["inputType"])
        selected.append(sample)
        if len(selected) == max_items:
            break
    return selected


def prepare_description_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """설명 생성에 사용할 유형별 본문을 정규화한다."""
    prepared: list[dict[str, Any]] = []
    for item in items:
        normalized = dict(item)
        if str(item.get("inputType", "")).lower() != "url":
            prepared.append(normalized)
            continue

        try:
            payload = json.loads(str(item.get("input", "")))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue

        summary = payload.get("summary")
        content = payload.get("content")
        summary_text = usable_url_summary(summary)
        content_text = content.strip() if isinstance(content, str) else ""
        if not summary_text and not content_text:
            continue

        normalized["input"] = summary_text or content_text
        normalized["summary"] = summary_text
        normalized["content"] = content_text
        prepared.append(normalized)
    return prepared


def build_description_prompt(
    template: str,
    category_name: str,
    category_names: list[str],
    samples: list[dict[str, str]],
) -> str:
    sample_text = "\n\n".join(
        f"[{sample['testId']}] ({sample.get('inputType', 'unknown')}) "
        f"{sample['title']}\n{sample['input']}"
        for sample in samples
    )
    if not sample_text:
        sample_text = (
            "사용 가능한 샘플 데이터가 없습니다. "
            "카테고리 이름과 전체 카테고리 목록만 보고 설명과 예시를 생성하세요."
        )
    return (
        template.replace("{{CATEGORY_NAME}}", category_name)
        .replace("{{ALL_CATEGORY_NAMES}}", "\n".join(f"- {name}" for name in category_names))
        .replace("{{CATEGORY_SAMPLES}}", sample_text)
    )


def validate_generated_description(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("생성 결과는 JSON 객체여야 합니다")
    description = value.get("description")
    examples = value.get("examples")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("description은 비어 있지 않은 문자열이어야 합니다")
    if not isinstance(examples, list) or len(examples) != 3:
        raise ValueError("examples는 문자열 3개의 배열이어야 합니다")
    normalized_examples = []
    for example in examples:
        if not isinstance(example, str) or not example.strip():
            raise ValueError("examples의 각 값은 비어 있지 않은 문자열이어야 합니다")
        normalized_examples.append(example.strip())
    if len(set(normalized_examples)) != 3:
        raise ValueError("examples는 서로 달라야 합니다")
    return {"description": description.strip(), "examples": normalized_examples}
