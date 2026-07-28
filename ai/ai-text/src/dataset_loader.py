from pathlib import Path
import json
import re
MEMO_NAME_PATTERN = re.compile(r"^(?P<id>\d+)-(?P<title>.+)$")

def load_category_definitions(path: Path, memo_root: Path | None = None) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("카테고리 정의는 비어 있지 않은 배열이어야 합니다.")
    names: list[str] = []
    ids: list[str] = []
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError("각 카테고리 정의에는 문자열 name이 필요합니다.")
        if not isinstance(item.get("id"), str) or not item["id"].strip():
            raise ValueError(f"{item['name']}: 문자열 id가 필요합니다.")
        if not isinstance(item.get("description"), str) or not item["description"].strip():
            raise ValueError(f"{item['name']}: description이 필요합니다.")
        if not isinstance(item.get("examples"), list):
            raise ValueError(f"{item['name']}: examples는 배열이어야 합니다.")
        names.append(item["name"])
        ids.append(item["id"])
    if len(names) != len(set(names)):
        raise ValueError("카테고리 정의에 중복 name이 있습니다.")
    if len(ids) != len(set(ids)):
        raise ValueError("카테고리 정의에 중복 id가 있습니다.")
    if memo_root is not None:
        folder_categories = load_categories(memo_root)
        missing = set(folder_categories) - set(names)
        if missing:
            raise ValueError(f"설명이 없는 카테고리 폴더가 있습니다: {sorted(missing)}")
        data = [item for item in data if item["name"] in set(folder_categories)]
    return data

def load_categories(memo_root: Path) -> list[str]:
    if not memo_root.is_dir():
        raise ValueError(f"카테고리 루트가 없습니다: {memo_root}")
    categories = sorted(
        path.name for path in memo_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )
    if not categories:
        raise ValueError("카테고리 루트 아래에 카테고리 폴더가 하나 이상 필요합니다.")
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


def load_typed_test_dataset(
    test_root: Path,
    input_types: list[str] | tuple[str, ...] = ("all",),
) -> tuple[list[dict], list[str]]:
    """dataset/test/<카테고리>/<url|image|memo>의 TXT를 공통 테스트 데이터로 읽는다."""
    categories = load_categories(test_root)
    requested = {value.lower() for value in input_types}
    allowed = {"url", "image", "memo", "all"}
    invalid = requested - allowed
    if invalid:
        raise ValueError(f"지원하지 않는 입력 유형: {sorted(invalid)}")
    selected = {"url", "image", "memo"} if "all" in requested else requested
    if not selected:
        raise ValueError("입력 유형을 하나 이상 선택해야 합니다")

    items: list[dict] = []
    counters = {data_type: 0 for data_type in selected}
    for category in categories:
        category_root = test_root / category
        for data_type in sorted(selected):
            type_root = category_root / data_type
            if not type_root.is_dir():
                raise ValueError(f"입력 유형 폴더가 없습니다: {type_root}")
            files = sorted(
                (path for path in type_root.glob("*.txt") if path.is_file()),
                key=lambda path: path.name.casefold(),
            )
            for path in files:
                counters[data_type] += 1
                raw = path.read_text(encoding="utf-8").strip()
                if not raw:
                    raise ValueError(f"빈 테스트 파일입니다: {path}")
                title, content = _typed_test_content(path, data_type, raw)
                prefix = data_type.upper()
                items.append({
                    "testId": f"{prefix}-{counters[data_type]:03d}",
                    "type": prefix,
                    "inputType": data_type,
                    "input": content,
                    "title": title,
                    "sourceTitle": title,
                    "sourcePath": path.relative_to(test_root).as_posix(),
                    "idAutoAssigned": True,
                    "datasetType": f"test-{data_type}",
                    "expected": {
                        "categories": [category],
                        "requiredKeywords": [],
                        "summaryPoints": [],
                        "forbiddenClaims": [],
                    },
                })
    return items, categories


def load_flat_test_dataset(
    test_root: Path,
    input_types: list[str] | tuple[str, ...] = ("all",),
) -> tuple[list[dict], list[str]]:
    """<카테고리>/*.txt 구조의 JSON 결과 파일을 공통 테스트 데이터로 읽는다."""
    categories = load_categories(test_root)
    requested = {value.lower() for value in input_types}
    allowed = {"url", "image", "memo", "all"}
    invalid = requested - allowed
    if invalid:
        raise ValueError(f"지원하지 않는 입력 유형: {sorted(invalid)}")
    selected = {"url", "image", "memo"} if "all" in requested else requested
    if not selected:
        raise ValueError("입력 유형을 하나 이상 선택해야 합니다")

    parsed: list[tuple[Path, str, str, str]] = []
    for category in categories:
        files = sorted(
            (path for path in (test_root / category).glob("*.txt") if path.is_file()),
            key=lambda path: path.name.casefold(),
        )
        for path in files:
            raw = path.read_text(encoding="utf-8").strip()
            if not raw:
                raise ValueError(f"빈 테스트 파일입니다: {path}")
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}: 구조화 데이터는 JSON 객체여야 합니다") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}: 구조화 데이터는 JSON 객체여야 합니다")
            data_type = str(value.get("type", "")).lower()
            if data_type not in {"url", "image", "memo"}:
                raise ValueError(f"{path}: 지원하지 않는 result.type입니다: {value.get('type')}")
            if data_type not in selected:
                continue
            title, content = _typed_test_content(path, data_type, raw)
            parsed.append((path, category, data_type, content))

    counters = {data_type: 0 for data_type in selected}
    items: list[dict] = []
    for path, category, data_type, content in parsed:
        counters[data_type] += 1
        value = json.loads(content)
        title = (
            str(value.get("url", "")).strip()
            if data_type == "url"
            else str(value.get("title") or path.stem).strip()
        )
        prefix = data_type.upper()
        items.append({
            "testId": f"{prefix}-{counters[data_type]:03d}",
            "type": prefix,
            "inputType": data_type,
            "input": content,
            "title": title,
            "sourceTitle": title,
            "sourcePath": path.relative_to(test_root).as_posix(),
            "sourceRoot": str(test_root.resolve()),
            "idAutoAssigned": True,
            "datasetType": f"tester-{data_type}",
            "expected": {
                "categories": [category],
                "requiredKeywords": [],
                "summaryPoints": [],
                "forbiddenClaims": [],
            },
        })
    if not items:
        raise ValueError("선택한 입력 유형에 해당하는 테스트 데이터가 없습니다")
    return items, categories


def _typed_test_content(path: Path, data_type: str, raw: str) -> tuple[str, str]:
    if data_type == "memo":
        return path.stem, raw
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: {data_type} 데이터는 JSON 객체여야 합니다") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: {data_type} 데이터는 JSON 객체여야 합니다")
    declared_type = str(value.get("type", "")).lower()
    if declared_type and declared_type != data_type:
        raise ValueError(
            f"{path}: 폴더 유형 {data_type}과 result.type {value.get('type')}이 다릅니다"
        )
    if data_type == "url":
        url = str(value.get("url", "")).strip()
        if not url:
            raise ValueError(f"{path}: URL 데이터에 url이 없습니다")
        title = url
    else:
        title = str(value.get("title") or path.stem).strip()
    return title, json.dumps(value, ensure_ascii=False, separators=(",", ":"))
