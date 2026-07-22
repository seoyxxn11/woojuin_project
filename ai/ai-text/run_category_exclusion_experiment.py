from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.dataset_loader import load_categories, load_category_definitions, load_memo_dataset
from src.model_config import safe_filename
from src.ollama_client import OllamaClient, performance
from src.result_writer import write_json


ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = "qwen3:8b"


SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "category": {"type": "string", "minLength": 1},
        "isNewCategory": {"type": "boolean"},
        "reason": {"type": "string", "minLength": 1},
        "newCategoryDescription": {"type": "string"},
    },
    "required": ["category", "isNewCategory", "reason", "newCategoryDescription"],
}


def build_prompt(item: dict[str, Any], definitions: list[dict[str, Any]]) -> str:
    category_lines = []
    for definition in definitions:
        examples = ", ".join(definition.get("examples", [])) or "없음"
        category_lines.append(
            f"- {definition['name']}: {definition['description']} (예: {examples})"
        )
    return f"""당신은 한국어 메모 카테고리 분류기입니다.

아래 기존 카테고리 중 메모와 자연스럽게 맞는 것이 있으면 하나를 선택하세요.
기존 카테고리에 억지로 끼워 맞추지 마세요.
적합한 기존 카테고리가 없으면 앞으로 비슷한 메모에도 재사용할 수 있는 새 카테고리 이름을 만드세요.
새 카테고리는 너무 구체적인 문장이나 일회성 이름이 아니라 짧은 분류명이어야 합니다.

기존 카테고리:
{chr(10).join(category_lines)}

판정 규칙:
- 기존 카테고리를 선택하면 isNewCategory는 false이고 newCategoryDescription은 빈 문자열입니다.
- 새 카테고리를 만들면 isNewCategory는 true이고 newCategoryDescription에 범위를 한 문장으로 설명합니다.
- category에는 최종 선택하거나 생성한 카테고리 이름 하나만 씁니다.
- reason에는 선택 근거를 간결하게 씁니다.
- JSON 객체만 출력합니다.

메모 제목:
{item.get('title', '')}

메모 내용:
{item['input']}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="특정 카테고리를 제외한 신규 카테고리 생성 실험")
    parser.add_argument("--excluded-category", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output")
    options = parser.parse_args()
    excluded_category = options.excluded_category
    model = options.model
    output = Path(options.output).resolve() if options.output else (
        ROOT / "REPORT" / "category-exclusion-experiment"
        / f"{safe_filename(model)}-without-{safe_filename(excluded_category)}.json"
    )
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    memo_root = ROOT / "dataset" / "memo"
    categories = load_categories(memo_root)
    if excluded_category not in categories:
        raise ValueError(f"제외할 카테고리가 없습니다: {excluded_category}")
    allowed_categories = [category for category in categories if category != excluded_category]
    definitions = [
        item for item in load_category_definitions(ROOT / "config" / "categories.json", memo_root)
        if item["name"] in allowed_categories
    ]
    target_items = [
        item for item in load_memo_dataset(memo_root, categories)
        if item["expected"]["categories"] == [excluded_category]
    ]
    client = OllamaClient(
        config["ollamaBaseUrl"],
        config["connectTimeoutSeconds"],
        config["readTimeoutSeconds"],
    )
    installed = client.models()
    if model not in installed:
        raise ValueError(f"Ollama 모델이 설치되어 있지 않습니다: {model}")
    results: list[dict[str, Any]] = []
    for index, item in enumerate(target_items, 1):
        print(f"[{index}/{len(target_items)}] {item['testId']} {item.get('title', '')}")
        prompt = build_prompt(item, definitions)
        _, response = client.chat(
            model,
            prompt,
            config["temperature"],
            config["keepAlive"],
            SCHEMA,
            config.get("seed"),
            config.get("contextLength"),
            config.get("thinking"),
        )
        raw_text = str(response.get("message", {}).get("content", ""))
        try:
            parsed = json.loads(raw_text)
            parse_error = None
        except json.JSONDecodeError as exc:
            parsed = None
            parse_error = str(exc)
        results.append({
            "testId": item["testId"],
            "title": item.get("title", ""),
            "sourcePath": item.get("sourcePath", ""),
            "originalCategory": excluded_category,
            "input": item["input"],
            "rawResponse": raw_text,
            "parsedResponse": parsed,
            "parseError": parse_error,
            "performance": performance(response),
        })
    write_json(output, {
        "metadata": {
            "model": model,
            "excludedCategory": excluded_category,
            "allowedCategories": allowed_categories,
            "targetCount": len(target_items),
            "executedAt": datetime.now().astimezone().isoformat(),
            "rule": "기존 카테고리에 적합하지 않으면 새 카테고리 생성",
        },
        "results": results,
    })
    print(f"[OK] {output}")


if __name__ == "__main__":
    main()
