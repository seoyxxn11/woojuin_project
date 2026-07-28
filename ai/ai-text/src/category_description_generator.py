from __future__ import annotations

from typing import Any


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
        selected.append({
            "testId": str(item.get("testId", "")),
            "title": str(item.get("title", "")).strip(),
            "input": str(item.get("input", "")).strip()[:max_chars_per_item],
        })
        if len(selected) == max_items:
            break
    if not selected:
        raise ValueError(f"카테고리 데이터가 없습니다: {category_name}")
    return selected


def build_description_prompt(
    template: str,
    category_name: str,
    category_names: list[str],
    samples: list[dict[str, str]],
) -> str:
    sample_text = "\n\n".join(
        f"[{sample['testId']}] {sample['title']}\n{sample['input']}" for sample in samples
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
