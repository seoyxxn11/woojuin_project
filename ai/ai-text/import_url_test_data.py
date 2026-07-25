from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = ROOT / "dataset" / "test"
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="URL 테스트 JSONL의 result 객체를 정답 카테고리별 TXT로 저장"
    )
    parser.add_argument("export_file", type=Path, help="index/url/expected/result JSONL 파일")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{line_number}행: JSON 객체가 아닙니다")
        expected = value.get("expected")
        result = value.get("result")
        if not isinstance(expected, str) or not expected.strip():
            raise ValueError(f"{line_number}행: expected가 비어 있습니다")
        if not isinstance(result, dict):
            raise ValueError(f"{line_number}행: result 객체가 없습니다")
        if result.get("type") != "URL":
            raise ValueError(f"{line_number}행: result.type이 URL이 아닙니다")
        if not isinstance(result.get("url"), str) or not result["url"].strip():
            raise ValueError(f"{line_number}행: result.url이 비어 있습니다")
        rows.append(value)
    if not rows:
        raise ValueError("처리할 URL 데이터가 없습니다")
    return rows


def url_filename(url: str) -> str:
    """URL을 알아볼 수 있게 유지하면서 Windows에서 유효한 TXT 파일명으로 바꾼다."""
    name = INVALID_FILENAME_CHARS.sub("_", url).rstrip(" .")
    if not name or name.upper() in RESERVED_NAMES:
        name = f"url_{hashlib.sha256(url.encode('utf-8')).hexdigest()[:12]}"
    max_stem_length = 180
    if len(name) > max_stem_length:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
        name = f"{name[:max_stem_length - 13]}_{digest}"
    return f"{name}.txt"


def import_rows(rows: list[dict[str, Any]], output_root: Path) -> list[Path]:
    planned: list[tuple[Path, dict[str, Any]]] = []
    seen: dict[Path, str] = {}
    categories = sorted({str(row["expected"]).strip() for row in rows})

    for category in categories:
        for data_type in ("url", "image", "memo"):
            directory = output_root / category / data_type
            directory.mkdir(parents=True, exist_ok=True)
            keep = directory / ".gitkeep"
            if not keep.exists():
                keep.write_text("", encoding="utf-8")

    for row in rows:
        result = row["result"]
        url = str(result["url"]).strip()
        destination = output_root / str(row["expected"]).strip() / "url" / url_filename(url)
        previous = seen.get(destination)
        if previous is not None and previous != url:
            raise ValueError(f"파일명 충돌: {previous} / {url}")
        if destination.exists() and destination.name != ".gitkeep":
            raise ValueError(f"기존 파일과 충돌합니다: {destination}")
        seen[destination] = url
        planned.append((destination, result))

    for destination, result in planned:
        destination.write_text(
            json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    return [destination for destination, _ in planned]


def main() -> int:
    options = parse_args()
    rows = load_rows(options.export_file.resolve())
    written = import_rows(rows, options.output_root.resolve())
    print(f"[OK] URL 테스트 데이터 {len(written)}건 저장")
    print(f"[OK] 출력 루트: {options.output_root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
