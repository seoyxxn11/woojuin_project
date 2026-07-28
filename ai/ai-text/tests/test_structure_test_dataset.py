import json
from pathlib import Path

import pytest

from structure_test_dataset import load_rows, structure_export


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_structure_export_groups_each_result_by_source_and_category(tmp_path: Path) -> None:
    source = tmp_path / "새 데이터.txt"
    rows = [
        {
            "index": 7,
            "expected": "생활·할 일",
            "result": {"type": "URL", "title": "청소 루틴", "content": "본문"},
        },
        {
            "index": 8,
            "expected": "학습·지식",
            "result": {"type": "MEMO", "title": "Redis 공부", "content": "메모"},
        },
    ]
    write_jsonl(source, rows)

    written = structure_export(source, tmp_path / "dataset" / "tester")

    assert [path.relative_to(tmp_path).as_posix() for path in written] == [
        "dataset/tester/새 데이터/생활·할 일/0007-url.txt",
        "dataset/tester/새 데이터/학습·지식/0008-memo.txt",
    ]
    assert json.loads(written[0].read_text(encoding="utf-8")) == rows[0]["result"]


def test_structure_export_does_not_overwrite_existing_folder_by_default(
    tmp_path: Path,
) -> None:
    source = tmp_path / "export.txt"
    write_jsonl(
        source,
        [{"index": 0, "expected": "기타", "result": {"type": "URL"}}],
    )
    structure_export(source, tmp_path / "tester")

    with pytest.raises(ValueError, match="이미 있습니다"):
        structure_export(source, tmp_path / "tester")


def test_load_rows_reports_invalid_line(tmp_path: Path) -> None:
    source = tmp_path / "broken.txt"
    source.write_text('{"expected":"기타","result":{}}\nnot-json\n', encoding="utf-8")

    with pytest.raises(ValueError, match="2행"):
        load_rows(source)
