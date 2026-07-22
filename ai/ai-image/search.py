from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from evaluate import load_results


ROOT = Path(__file__).resolve().parent
CATEGORY_ALIASES = {
    "문서": "DOCUMENT",
    "음식": "FOOD",
    "장소": "PLACE",
    "제품": "PRODUCT",
    "상품": "PRODUCT",
    "사람": "PERSON",
    "인물": "PERSON",
    "스크린샷": "SCREENSHOT",
    "기타": "OTHER",
}


def normalize_category(value: str) -> str:
    normalized = value.strip()
    return CATEGORY_ALIASES.get(normalized, normalized.upper())


def latest_result(results_dir: Path) -> Path:
    candidates = [
        path
        for path in results_dir.glob("*.jsonl")
        if path.is_file() and path.stat().st_size > 0
    ]
    if not candidates:
        raise FileNotFoundError("검색할 결과 JSONL이 없습니다.")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def build_search_index(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index: list[dict[str, Any]] = []
    for record in records:
        result = record.get("result")
        if record.get("error") is not None or not isinstance(result, dict):
            continue
        truth = record.get("ground_truth", {})
        index.append(
            {
                "id": record.get("sample_id"),
                "image_file": truth.get("file"),
                "title": result.get("title", ""),
                "description": result.get("description", ""),
                "category": result.get("category", "OTHER"),
                "tags": result.get("tags", []),
                "ocr_text": result.get("ocr_text", ""),
                "objects": result.get("objects", []),
                "confidence": result.get("confidence"),
                "model": record.get("model"),
            }
        )
    return index


def search_by_category(
    index: list[dict[str, Any]],
    category: str,
) -> list[dict[str, Any]]:
    normalized = normalize_category(category)
    return [item for item in index if item.get("category") == normalized]


def write_search_index(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(build_search_index(records), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="모델 결과의 카테고리 검색")
    parser.add_argument(
        "--category",
        required=True,
        help="DOCUMENT 또는 문서처럼 검색할 카테고리 입력",
    )
    parser.add_argument(
        "--result",
        type=Path,
        help="검색할 결과 JSONL. 생략하면 가장 최근 결과 사용",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result_path = args.result or latest_result(ROOT / "results")
    if not result_path.is_absolute():
        result_path = ROOT / result_path

    index = build_search_index(load_results(result_path))
    matches = search_by_category(index, args.category)
    print(
        json.dumps(
            {
                "query": normalize_category(args.category),
                "count": len(matches),
                "items": matches,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
