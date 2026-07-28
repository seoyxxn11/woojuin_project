from pathlib import Path

from create_stratified_folds import create_folds


def test_create_folds_uses_every_item_once_for_classification(tmp_path: Path) -> None:
    source = tmp_path / "source"
    originals: set[str] = set()
    for category in ("가", "나"):
        folder = source / category
        folder.mkdir(parents=True)
        for index in range(5):
            path = folder / f"{index}.txt"
            path.write_text(f"{category}-{index}", encoding="utf-8")
            originals.add(f"{category}/{path.name}")

    output = tmp_path / "folds"
    create_folds(source, output, folds=5)

    tested: set[str] = set()
    for fold in range(1, 6):
        fold_root = output / f"fold-{fold}"
        train = list((fold_root / "category-summary").glob("*/*.txt"))
        test = list((fold_root / "classification").glob("*/*.txt"))
        assert len(train) == 8
        assert len(test) == 2
        assert {path.parent.name for path in test} == {"가", "나"}
        tested.update(
            f"{path.parent.name}/{path.name}"
            for path in test
        )

    assert tested == originals
