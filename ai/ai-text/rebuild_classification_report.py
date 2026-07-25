from __future__ import annotations

import argparse
import json
from pathlib import Path

from main import ROOT, write_classification_outputs
from src.dataset_loader import load_category_definitions
from src.result_writer import write_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description="기존 category-only 결과에서 단일 모델 분류 보고서를 다시 생성"
    )
    parser.add_argument("result_dir", type=Path)
    options = parser.parse_args()
    result_dir = options.result_dir.resolve()
    metadata = json.loads((result_dir / "run-metadata.json").read_text(encoding="utf-8"))
    rows = json.loads((result_dir / "evaluation-results.json").read_text(encoding="utf-8"))
    if metadata.get("testMode") != "category-only":
        raise ValueError("category-only 실행 결과만 지원합니다")
    definitions = load_category_definitions(ROOT / "config" / "categories.json")
    categories = list(metadata["categories"])
    definitions = [item for item in definitions if item["name"] in set(categories)]
    write_json(result_dir / "category-descriptions.json", definitions)
    write_classification_outputs(result_dir, metadata, rows, categories, definitions)
    print(f"[OK] 분류 보고서 재생성: {result_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
