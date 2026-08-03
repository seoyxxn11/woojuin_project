from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class DynamicCategoryScenario:
    id: str
    label: str
    seed_count: int
    accumulate: bool = False
    baseline: bool = False


SCENARIOS: dict[str, DynamicCategoryScenario] = {
    "baseline11": DynamicCategoryScenario(
        "baseline11", "기존 11개만 사용 (기준 테스트)", 11, baseline=True
    ),
    "existing11-ai": DynamicCategoryScenario(
        "existing11-ai", "기존 11개 + AI 생성", 11
    ),
    "ai-only": DynamicCategoryScenario(
        "ai-only", "기존 카테고리 없이 AI 생성", 0
    ),
    "existing3-ai": DynamicCategoryScenario(
        "existing3-ai", "기존 3개 + AI 생성", 3
    ),
    "existing5-ai": DynamicCategoryScenario(
        "existing5-ai", "기존 5개 + AI 생성", 5
    ),
    "existing7-ai": DynamicCategoryScenario(
        "existing7-ai", "기존 7개 + AI 생성", 7
    ),
    "cumulative": DynamicCategoryScenario(
        "cumulative", "생성 카테고리 누적 적용", 0, True
    ),
}

SCENARIO_ALIASES = {
    "0": "baseline11",
    "1": "existing11-ai",
    "2": "ai-only",
    "3": "existing3-ai",
    "4": "existing5-ai",
    "5": "existing7-ai",
    "6": "cumulative",
}


def resolve_scenarios(values: Iterable[str]) -> list[DynamicCategoryScenario]:
    requested = [str(value).strip().lower() for value in values if str(value).strip()]
    if not requested:
        raise ValueError("실행할 시나리오를 하나 이상 선택하세요.")
    expanded: list[str] = []
    for value in requested:
        value = SCENARIO_ALIASES.get(value, value)
        if value == "all":
            expanded.extend(SCENARIOS)
        elif value == "reduced-ai":
            expanded.extend(("existing3-ai", "existing5-ai", "existing7-ai"))
        elif value in SCENARIOS:
            expanded.append(value)
        else:
            raise ValueError(f"지원하지 않는 시나리오: {value}")
    return [SCENARIOS[value] for value in dict.fromkeys(expanded)]


def seed_definitions(
    definitions: list[dict[str, Any]], seed_count: int
) -> list[dict[str, Any]]:
    """현재 데이터셋에 존재하는 카테고리의 설정 파일 순서를 사용한다."""
    candidates = [dict(item) for item in definitions]
    if seed_count < 0:
        raise ValueError("기존 카테고리 개수는 0 이상이어야 합니다.")
    if seed_count > len(candidates):
        raise ValueError(
            f"기존 카테고리 {seed_count}개가 필요하지만 사용 가능한 카테고리는 "
            f"{len(candidates)}개입니다."
        )
    return candidates[:seed_count]


def dynamic_category_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "categoryName": {"type": "string", "minLength": 1},
            "categoryDescription": {"type": "string", "minLength": 1},
            "categoryOrigin": {
                "type": "string",
                "enum": ["EXISTING", "GENERATED"],
            },
            "reason": {"type": "string", "minLength": 1},
        },
        "required": [
            "categoryName",
            "categoryDescription",
            "categoryOrigin",
            "reason",
        ],
        "additionalProperties": False,
    }


def format_catalog(definitions: list[dict[str, Any]]) -> str:
    if not definitions:
        return "- 없음 (반드시 새 카테고리를 생성하세요)"
    lines = []
    for item in definitions:
        origin = "AI 생성" if item.get("origin") == "AI_GENERATED" else "기존"
        lines.append(
            f"- {item['name']} [{origin}]: {item.get('description', '').strip()}"
        )
    return "\n".join(lines)


def build_dynamic_prompt(
    template: str,
    content: str,
    title: str,
    definitions: list[dict[str, Any]],
) -> str:
    required = ("{{AVAILABLE_CATEGORIES}}", "{{CONTENT}}", "{{TITLE_CONTEXT}}")
    missing = [placeholder for placeholder in required if placeholder not in template]
    if missing:
        raise ValueError(f"동적 카테고리 프롬프트 필드 누락: {', '.join(missing)}")
    title_context = f"입력 제목:\n{title.strip()}\n\n" if title.strip() else ""
    return (
        template.replace("{{AVAILABLE_CATEGORIES}}", format_catalog(definitions))
        .replace("{{TITLE_CONTEXT}}", title_context)
        .replace("{{CONTENT}}", content)
    )


def generated_category_id(name: str) -> str:
    digest = hashlib.sha1(name.strip().casefold().encode("utf-8")).hexdigest()[:10]
    return f"AI-{digest.upper()}"


class CategoryCatalog:
    def __init__(self, definitions: list[dict[str, Any]]) -> None:
        self._definitions: list[dict[str, Any]] = []
        for item in definitions:
            normalized = dict(item)
            normalized.setdefault("origin", "EXISTING")
            self._append(normalized)

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._definitions]

    def find(self, name: str) -> dict[str, Any] | None:
        key = name.strip().casefold()
        return next(
            (dict(item) for item in self._definitions if item["name"].casefold() == key),
            None,
        )

    def add_generated(self, name: str, description: str) -> tuple[dict[str, Any], bool]:
        existing = self.find(name)
        if existing is not None:
            return existing, False
        item = {
            "id": generated_category_id(name),
            "name": name.strip(),
            "description": description.strip(),
            "examples": [],
            "origin": "AI_GENERATED",
        }
        self._append(item)
        return dict(item), True

    def _append(self, item: dict[str, Any]) -> None:
        name = str(item.get("name", "")).strip()
        if not name:
            raise ValueError("카테고리 이름은 비어 있을 수 없습니다.")
        if self.find(name) is not None:
            raise ValueError(f"중복 카테고리 이름: {name}")
        item["name"] = name
        self._definitions.append(item)


def parse_dynamic_response(
    raw: str, available_definitions: list[dict[str, Any]]
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "rawResponse": raw,
        "jsonValid": False,
        "schemaValid": False,
        "extraTextDetected": False,
        "parsedResponse": None,
        "validationError": "",
        "deduplicatedToExisting": False,
    }
    candidate, span = _balanced_json(raw.strip())
    if candidate is None or span is None:
        result["validationError"] = "JSON 객체를 찾지 못했습니다."
        return result
    result["extraTextDetected"] = bool(
        raw.strip()[: span[0]].strip() or raw.strip()[span[1] :].strip()
    )
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        result["validationError"] = str(exc)
        return result
    result["jsonValid"] = True
    if not isinstance(parsed, dict):
        result["validationError"] = "응답은 JSON 객체여야 합니다."
        return result
    required = {
        "categoryName",
        "categoryDescription",
        "categoryOrigin",
        "reason",
    }
    if set(parsed) != required:
        result["validationError"] = (
            "응답 필드는 categoryName, categoryDescription, categoryOrigin, reason만 허용합니다."
        )
        return result
    values = {key: str(parsed.get(key, "")).strip() for key in required}
    if not all(values.values()):
        result["validationError"] = "모든 응답 필드는 비어 있지 않아야 합니다."
        return result
    origin = values["categoryOrigin"].upper()
    if origin not in {"EXISTING", "GENERATED"}:
        result["validationError"] = "categoryOrigin은 EXISTING 또는 GENERATED여야 합니다."
        return result
    by_name = {
        str(item["name"]).strip().casefold(): item for item in available_definitions
    }
    matched = by_name.get(values["categoryName"].casefold())
    if origin == "EXISTING" and matched is None:
        result["validationError"] = "EXISTING 카테고리는 제공된 이름과 정확히 일치해야 합니다."
        return result
    if origin == "GENERATED" and matched is not None:
        origin = "EXISTING"
        values["categoryName"] = str(matched["name"])
        values["categoryDescription"] = str(matched.get("description") or values["categoryDescription"])
        result["deduplicatedToExisting"] = True
    values["categoryOrigin"] = origin
    result["parsedResponse"] = values
    result["schemaValid"] = not result["extraTextDetected"]
    if result["extraTextDetected"]:
        result["validationError"] = "JSON 외 텍스트가 포함되었습니다."
    return result


def _balanced_json(text: str) -> tuple[str | None, tuple[int, int] | None]:
    for start, character in enumerate(text):
        if character != "{":
            continue
        depth = 0
        quoted = False
        escaped = False
        for index in range(start, len(text)):
            current = text[index]
            if quoted:
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    quoted = False
            elif current == '"':
                quoted = True
            elif current == "{":
                depth += 1
            elif current == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1], (start, index + 1)
    return None, None


def content_summary(content: str) -> str:
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return ""
    if not isinstance(value, dict):
        return ""
    return str(
        value.get("summary")
        or value.get("preview", {}).get("description")
        or value.get("content")
        or ""
    ).strip()
