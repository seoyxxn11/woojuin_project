import json
from pathlib import Path

from src.dataset_loader import load_flat_test_dataset


def test_load_flat_test_dataset_reads_structured_category_files(tmp_path: Path) -> None:
    source = tmp_path / "생활·할 일" / "0000-url.txt"
    source.parent.mkdir(parents=True)
    source.write_text(
        json.dumps(
            {
                "type": "URL",
                "url": "https://example.com/cleaning",
                "content": "청소 루틴",
                "summary": None,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    items, categories = load_flat_test_dataset(tmp_path, ["url"])

    assert categories == ["생활·할 일"]
    assert len(items) == 1
    assert items[0]["testId"] == "URL-001"
    assert items[0]["sourcePath"] == "생활·할 일/0000-url.txt"
    assert items[0]["sourceRoot"] == str(tmp_path.resolve())
    assert items[0]["expected"]["categories"] == ["생활·할 일"]
