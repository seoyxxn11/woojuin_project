from pathlib import Path
import json
import re
MEMO_NAME_PATTERN = re.compile(r"^(?P<id>\d+)-(?P<title>.+)$")

def load_category_definitions(path: Path, memo_root: Path | None = None) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("카테고리 정의는 비어 있지 않은 배열이어야 합니다.")
    names: list[str] = []
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError("각 카테고리 정의에는 문자열 name이 필요합니다.")
        if not isinstance(item.get("description"), str) or not item["description"].strip():
            raise ValueError(f"{item['name']}: description이 필요합니다.")
        if not isinstance(item.get("examples"), list):
            raise ValueError(f"{item['name']}: examples는 배열이어야 합니다.")
        names.append(item["name"])
    if len(names) != len(set(names)):
        raise ValueError("카테고리 정의에 중복 name이 있습니다.")
    if memo_root is not None and set(names) != set(load_categories(memo_root)):
        raise ValueError("카테고리 정의와 dataset/memo 폴더명이 일치하지 않습니다.")
    return data

def load_categories(memo_root: Path) -> list[str]:
    if not memo_root.is_dir():
        raise ValueError(f"메모 카테고리 루트가 없습니다: {memo_root}")
    categories = sorted(
        path.name for path in memo_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )
    if not categories:
        raise ValueError("dataset/memo 아래에 카테고리 폴더가 하나 이상 필요합니다.")
    return categories

def validate_expected_categories(data: list[dict], categories: list[str]) -> None:
    allowed = set(categories)
    for item in data:
        invalid = set(item["expected"].get("categories", [])) - allowed
        if invalid:
            raise ValueError(
                f"{item['testId']}: 현재 카테고리 폴더에 없는 기대값 {sorted(invalid)}"
            )

def load_dataset(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list): raise ValueError("데이터셋 최상위 값은 배열이어야 합니다.")
    for item in data:
        missing = {"testId", "input", "expected"} - item.keys()
        if missing: raise ValueError(f"{item.get('testId', '?')}: 필드 누락 {sorted(missing)}")
        item.setdefault("title", "")
        item.setdefault("sourcePath", path.name)
        item.setdefault("idAutoAssigned", False)
        item["datasetType"] = "json"
    return data

def load_memo_dataset(memo_root: Path, categories: list[str] | None = None) -> list[dict]:
    """카테고리 폴더의 UTF-8 텍스트 파일을 테스트 데이터로 변환합니다."""
    if not memo_root.exists():
        return []
    categories = categories or load_categories(memo_root)
    files = sorted(
        (path for path in memo_root.glob("*/*.txt") if path.is_file()),
        key=lambda path: path.relative_to(memo_root).as_posix().casefold(),
    )
    explicit_ids: dict[int, Path] = {}
    parsed_files: list[tuple[Path, int | None, str]] = []
    for path in files:
        category = path.parent.name
        if category not in categories:
            raise ValueError(f"허용되지 않은 메모 카테고리 폴더입니다: {category}")
        match = MEMO_NAME_PATTERN.match(path.stem)
        memo_id = int(match.group("id")) if match else None
        title = match.group("title").strip() if match else path.stem.strip()
        if not title:
            raise ValueError(f"메모 제목이 비어 있습니다: {path}")
        if memo_id is not None:
            if memo_id in explicit_ids:
                raise ValueError(f"중복 메모 ID {memo_id}: {explicit_ids[memo_id]} / {path}")
            explicit_ids[memo_id] = path
        parsed_files.append((path, memo_id, title))
    used_ids = set(explicit_ids)
    next_id = 1
    result: list[dict] = []
    for path, memo_id, title in parsed_files:
        auto_assigned = memo_id is None
        if auto_assigned:
            while next_id in used_ids:
                next_id += 1
            memo_id = next_id
            used_ids.add(memo_id)
            next_id += 1
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            raise ValueError(f"빈 메모 파일은 테스트할 수 없습니다: {path}")
        result.append({
            "testId": f"TEXT-{memo_id:03d}",
            "type": "MEMO_FILE",
            "input": content,
            "title": title,
            "sourceTitle": title,
            "sourcePath": path.relative_to(memo_root).as_posix(),
            "idAutoAssigned": auto_assigned,
            "datasetType": "memo",
            "expected": {
                "categories": [path.parent.name],
                "requiredKeywords": [],
                "summaryPoints": [],
                "forbiddenClaims": [],
            },
        })
    return result
