from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.category_description_generator import (
    DESCRIPTION_SCHEMA,
    build_description_prompt,
    prepare_description_items,
    select_category_samples,
    validate_generated_description,
)
from src.dataset_loader import load_categories, load_category_definitions, load_typed_test_dataset
from src.ollama_client import OllamaClient, OllamaError, performance
from src.result_writer import write_json


ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = "qwen3:8b"
PROMPT_VERSION = "category-description-v1"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="카테고리별 실제 데이터를 이용한 설명·예시 생성")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--categories", nargs="+", help="일부 카테고리만 생성")
    parser.add_argument("--max-items", type=int, default=20, help="카테고리당 최대 샘플 수")
    parser.add_argument("--max-chars-per-item", type=int, default=1200, help="샘플당 최대 글자 수")
    parser.add_argument("--output", help="재사용할 카테고리 정의 JSON 경로")
    parser.add_argument("--overwrite", action="store_true", help="기존 출력 파일 덮어쓰기")
    parser.add_argument("--dry-run", action="store_true", help="모델 호출 없이 입력 계획 확인")
    return parser.parse_args(argv)


def default_output_path(now: datetime) -> Path:
    return ROOT / "config" / "generated" / f"category-descriptions-{now:%Y%m%d-%H%M%S}.json"


def main(argv: list[str] | None = None) -> int:
    options = parse_args(argv)
    now = datetime.now().astimezone()
    output = Path(options.output).resolve() if options.output else default_output_path(now)
    metadata_output = output.with_name(f"{output.stem}.metadata.json")
    if output.exists() and not options.overwrite:
        raise ValueError(f"출력 파일이 이미 있습니다. --overwrite가 필요합니다: {output}")

    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    test_root = ROOT / "dataset" / "test"
    category_names = load_categories(test_root)
    base_definitions = load_category_definitions(ROOT / "config" / "categories.json", test_root)
    typed_items, _ = load_typed_test_dataset(test_root, ["all"])
    items = prepare_description_items(typed_items)
    requested = options.categories or category_names
    unknown = set(requested) - set(category_names)
    if unknown:
        raise ValueError(f"없는 카테고리: {sorted(unknown)}")

    samples_by_category = {
        name: select_category_samples(
            items, name, max_items=options.max_items,
            max_chars_per_item=options.max_chars_per_item,
        )
        for name in requested
    }
    print(f"카테고리 {len(requested)}개, 샘플 {sum(map(len, samples_by_category.values()))}개")
    print(f"출력: {output}")
    if options.dry_run:
        for name, samples in samples_by_category.items():
            print(f"- {name}: {len(samples)}개")
        print("[DRY-RUN] 모델을 호출하거나 파일을 저장하지 않았습니다")
        return 0

    client = OllamaClient(
        config["ollamaBaseUrl"], config["connectTimeoutSeconds"], config["readTimeoutSeconds"]
    )
    installed = client.models()
    if options.model not in installed and not any(
        name.split(":")[0] == options.model for name in installed
    ):
        raise ValueError(f"Ollama 모델이 설치되어 있지 않습니다: {options.model}")
    template = (ROOT / "prompts" / "category-description-generation-v1.txt").read_text(encoding="utf-8")
    generated_by_name: dict[str, dict[str, Any]] = {}
    calls: list[dict[str, Any]] = []
    for index, name in enumerate(requested, 1):
        print(f"[{index}/{len(requested)}] {name}")
        prompt = build_description_prompt(template, name, category_names, samples_by_category[name])
        try:
            _, response = client.chat(
                options.model, prompt, config["temperature"], config["keepAlive"],
                DESCRIPTION_SCHEMA, config.get("seed"), config.get("contextLength"),
                config.get("thinking"),
            )
        except OllamaError as exc:
            raise RuntimeError(f"{name} 설명 생성 실패 ({exc.error_type}): {exc}") from exc
        raw = str(response.get("message", {}).get("content", ""))
        try:
            generated = validate_generated_description(json.loads(raw))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"{name} 생성 응답 검증 실패: {exc}\n원문: {raw[:500]}") from exc
        generated_by_name[name] = generated
        calls.append({
            "category": name,
            "sampleCount": len(samples_by_category[name]),
            "sourcePaths": [sample["testId"] for sample in samples_by_category[name]],
            "rawResponse": raw,
            "performance": performance(response),
        })

    definitions = []
    for definition in base_definitions:
        generated = generated_by_name.get(str(definition["name"]))
        definitions.append({**definition, **generated} if generated else definition)
    write_json(output, definitions)
    write_json(metadata_output, {
        "model": options.model,
        "promptVersion": PROMPT_VERSION,
        "createdAt": now.isoformat(),
        "output": str(output),
        "generatedCategories": requested,
        "sampleRoot": str(test_root),
        "urlSamplePolicy": "summary 우선, summary가 없으면 content, 둘 다 없으면 제외",
        "calls": calls,
    })
    print(f"[OK] 재사용 정의 저장: {output}")
    print(f"[OK] 생성 이력 저장: {metadata_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
