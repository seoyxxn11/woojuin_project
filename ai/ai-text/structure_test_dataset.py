from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = ROOT / "dataset" / "tester"
INVALID_PATH_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "JSONL TXT 파일을 "
            "dataset/tester/<입력 파일명>/<카테고리>/*.txt 구조로 분리"
        )
    )
    parser.add_argument(
        "export_files",
        type=Path,
        nargs="+",
        help="각 행이 expected/result 객체인 JSONL TXT 파일",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="같은 입력 파일명으로 만든 기존 폴더를 교체",
    )
    return parser.parse_args()


def safe_path_name(value: str, *, label: str) -> str:
    name = value.strip().rstrip(" .")
    if (
        not name
        or name in {".", ".."}
        or INVALID_PATH_CHARS.search(name)
        or name.upper() in RESERVED_NAMES
    ):
        raise ValueError(f"유효하지 않은 {label} 이름입니다: {value!r}")
    return name


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"{path.name} {line_number}행: 올바른 JSON 객체가 아닙니다"
            ) from error
        if not isinstance(value, dict):
            raise ValueError(f"{path.name} {line_number}행: JSON 객체가 아닙니다")

        expected = value.get("expected")
        result = value.get("result")
        if not isinstance(expected, str) or not expected.strip():
            raise ValueError(f"{path.name} {line_number}행: expected가 비어 있습니다")
        safe_path_name(expected, label="카테고리")
        if not isinstance(result, dict):
            raise ValueError(f"{path.name} {line_number}행: result 객체가 없습니다")
        rows.append(value)

    if not rows:
        raise ValueError(f"{path.name}: 처리할 데이터가 없습니다")
    return rows


def item_filename(row: dict[str, Any], sequence: int) -> str:
    index = row.get("index")
    number = index if isinstance(index, int) and index >= 0 else sequence
    item_type = row["result"].get("type")
    suffix = item_type.lower() if isinstance(item_type, str) and item_type else "item"
    suffix = INVALID_PATH_CHARS.sub("_", suffix).strip(" .") or "item"
    return f"{number:04d}-{suffix}.txt"


def structure_rows(
    rows: list[dict[str, Any]],
    destination: Path,
    *,
    overwrite: bool = False,
) -> list[Path]:
    if destination.exists():
        if not overwrite:
            raise ValueError(
                f"출력 폴더가 이미 있습니다: {destination} "
                "(교체하려면 --overwrite 사용)"
            )
        if not destination.is_dir():
            raise ValueError(f"출력 경로가 폴더가 아닙니다: {destination}")

    planned: list[tuple[Path, dict[str, Any]]] = []
    seen: set[Path] = set()
    for sequence, row in enumerate(rows):
        category = safe_path_name(str(row["expected"]), label="카테고리")
        path = destination / category / item_filename(row, sequence)
        if path in seen:
            raise ValueError(f"중복된 데이터 번호입니다: {path.name}")
        seen.add(path)
        planned.append((path, row["result"]))

    if overwrite:
        for old_file in destination.glob("*/*.txt"):
            old_file.unlink()

    written: list[Path] = []
    for path, result in planned:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return written


def structure_export(
    export_file: Path,
    output_root: Path,
    *,
    overwrite: bool = False,
) -> list[Path]:
    source = export_file.resolve()
    if not source.is_file():
        raise ValueError(f"입력 파일이 없습니다: {source}")
    folder_name = safe_path_name(source.stem, label="입력 파일")
    rows = load_rows(source)
    return structure_rows(rows, output_root.resolve() / folder_name, overwrite=overwrite)


def main() -> int:
    options = parse_args()
    total = 0
    for export_file in options.export_files:
        written = structure_export(
            export_file,
            options.output_root,
            overwrite=options.overwrite,
        )
        total += len(written)
        print(f"[OK] {export_file.name}: {len(written)}건 저장")
        print(f"[OK] 출력 폴더: {written[0].parents[1]}")
    print(f"[OK] 총 {total}건 구조화 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
