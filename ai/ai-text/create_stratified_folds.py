from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="카테고리별 균형을 유지하는 교차검증 데이터 폴더 생성"
    )
    parser.add_argument("dataset_root", type=Path, help="<카테고리>/*.txt 데이터셋")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def create_folds(source_root: Path, output_root: Path, folds: int = 5) -> None:
    source_root = source_root.resolve()
    output_root = output_root.resolve()
    if folds < 2:
        raise ValueError("--folds는 2 이상이어야 합니다")
    if not source_root.is_dir():
        raise ValueError(f"데이터셋 폴더가 없습니다: {source_root}")
    if output_root.exists():
        raise ValueError(f"출력 폴더가 이미 있습니다: {output_root}")

    categories = sorted(
        path for path in source_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )
    if not categories:
        raise ValueError("카테고리 폴더가 없습니다")

    category_files: dict[str, list[Path]] = {}
    for category in categories:
        files = sorted(
            (path for path in category.glob("*.txt") if path.is_file()),
            key=lambda path: path.name.casefold(),
        )
        if len(files) < folds:
            raise ValueError(
                f"{category.name}: {folds}-fold에 필요한 파일이 부족합니다 "
                f"({len(files)}개)"
            )
        category_files[category.name] = files

    for fold_index in range(folds):
        fold_root = output_root / f"fold-{fold_index + 1}"
        for category, files in category_files.items():
            for file_index, source in enumerate(files):
                group = "classification" if file_index % folds == fold_index else "category-summary"
                destination = fold_root / group / category / source.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)


def main() -> int:
    options = parse_args()
    source = options.dataset_root.resolve()
    output = (
        options.output.resolve()
        if options.output
        else source.with_name(f"{source.name}-{options.folds}fold")
    )
    create_folds(source, output, options.folds)
    print(f"[OK] {options.folds}-fold 데이터 생성: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
