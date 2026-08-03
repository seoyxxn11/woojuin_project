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


PRESET_SEEDS: dict[int, list[dict[str, Any]]] = {
    7: [
        {
            "id": "LIFE_HEALTH",
            "name": "생활·건강",
            "description": "개인 일정, 준비물, 청소, 정리, 행정 처리, 운동 계획, 신체 활동, 건강 관리 등 일상 행동과 건강에 관한 내용",
            "examples": ["주말 방 정리 계획", "기숙사 준비물", "주 3회 근력 운동 계획"],
        },
        {
            "id": "LEARNING_CAREER",
            "name": "학습·커리어",
            "description": "시험 공부, 강의, 개념 정리, 기술 구현, IT 참고 자료, 채용 공고, 면접, 이력서 등 배움과 경력 개발에 관한 내용",
            "examples": ["SQLD 시험 공부 계획", "JWT 재발급 구조 정리", "백엔드 면접 준비"],
        },
        {
            "id": "TRAVEL_PLACE",
            "name": "여행·장소",
            "description": "여행 일정, 방문할 장소, 교통, 숙소와 지역 탐방에 관한 내용",
            "examples": ["제주 여행 일정", "서울 전시회 방문 후보", "부산 숙소와 교통 계획"],
        },
        {
            "id": "FOOD_RESTAURANT",
            "name": "음식·맛집",
            "description": "요리법, 식재료, 식당, 메뉴, 맛집 방문과 식사 계획에 관한 내용",
            "examples": ["닭가슴살 볶음밥 레시피", "성수동 식당 후보", "김치찌개 조리 순서"],
        },
        {
            "id": "SHOPPING_PRODUCT",
            "name": "쇼핑·제품",
            "description": "상품 구매 후보, 제품 비교, 가격과 기능 검토, 구매 의사결정 중심의 내용",
            "examples": ["무선 키보드 구매 후보", "이어폰 배터리 성능 비교", "노트북 가격 확인"],
        },
        {
            "id": "MONEY_FINANCE",
            "name": "돈·재테크",
            "description": "예산, 저축, 투자, 보험, 세금, 대출과 자산 관리 등 개인 금융 중심의 내용",
            "examples": ["월간 예산 정리", "적금 금리 비교", "ETF 투자 기록"],
        },
        {
            "id": "CULTURE_IDEA",
            "name": "문화·아이디어",
            "description": "책, 영화, 드라마, 웹툰, 공연 감상 및 창작 아이디어, 서비스 발상, 영감 기록에 관한 내용",
            "examples": ["읽어볼 개발 에세이", "앱 기능 아이디어", "콘텐츠 기획 메모"],
        },
    ],
    5: [
        {
            "id": "LIFE_HEALTH",
            "name": "생활·건강",
            "description": "개인 일정, 준비물, 청소, 정리, 행정 처리, 운동 계획, 신체 활동, 건강 관리 등 일상 행동과 건강에 관한 내용",
            "examples": ["주말 방 정리 계획", "기숙사 준비물", "주 3회 근력 운동 계획"],
        },
        {
            "id": "LEARNING_CAREER",
            "name": "학습·커리어",
            "description": "시험 공부, 강의, 개념 정리, 기술 구현, IT 참고 자료, 채용 공고, 면접, 이력서 등 배움과 경력 개발에 관한 내용",
            "examples": ["SQLD 시험 공부 계획", "JWT 재발급 구조 정리", "백엔드 면접 준비"],
        },
        {
            "id": "PLACE_FOOD",
            "name": "장소·먹거리",
            "description": "여행 일정, 방문 장소, 숙소, 식당, 카페, 레시피, 맛집 등 장소와 음식에 관한 내용",
            "examples": ["제주 여행 일정", "성수동 식당 후보", "닭가슴살 볶음밥 레시피"],
        },
        {
            "id": "CONSUMPTION_FINANCE",
            "name": "소비·금융",
            "description": "상품 구매, 제품 비교, 가격 검토, 예산, 저축, 투자 등 경제 활동과 금융에 관한 내용",
            "examples": ["무선 키보드 구매 후보", "월간 예산 정리", "적금 금리 비교"],
        },
        {
            "id": "CULTURE_IDEA",
            "name": "문화·아이디어",
            "description": "책, 영화, 드라마, 웹툰, 공연 감상 및 창작 아이디어, 서비스 발상, 영감 기록에 관한 내용",
            "examples": ["읽어볼 개발 에세이", "앱 기능 아이디어", "콘텐츠 기획 메모"],
        },
    ],
    3: [
        {
            "id": "LIFE_MANAGEMENT",
            "name": "생활·관리",
            "description": "일상 할 일, 건강 관리, 운동, 예산 및 지출 관리 등 일상 생활 유지와 관리에 관한 내용",
            "examples": ["주말 방 정리 계획", "주 3회 근력 운동 계획", "월간 예산 정리"],
        },
        {
            "id": "LEARNING_GROWTH",
            "name": "학습·성장",
            "description": "공부, 강의, 개발 학습, 자격증, 채용 공고, 면접 등 자기계발과 성장에 관한 내용",
            "examples": ["SQLD 시험 공부 계획", "JWT 재발급 구조 정리", "백엔드 면접 준비"],
        },
        {
            "id": "INTEREST_EXPLORATION",
            "name": "관심·탐색",
            "description": "여행지, 맛집, 카페, 쇼핑 제품, 영화·드라마 등 문화 콘텐츠 및 아이디어 탐색에 관한 내용",
            "examples": [
                "제주 여행 일정",
                "성수동 식당 후보",
                "무선 키보드 구매 후보",
                "읽어볼 개발 에세이",
                "앱 기능 아이디어",
            ],
        },
    ],
}


def seed_definitions(
    definitions: list[dict[str, Any]], seed_count: int
) -> list[dict[str, Any]]:
    """축소 실험 조건(3개, 5개, 7개)의 통합 카테고리 프리셋 또는 기존 카테고리를 반환한다."""
    candidates = [dict(item) for item in definitions]
    if seed_count < 0:
        raise ValueError("기존 카테고리 개수는 0 이상이어야 합니다.")
    if seed_count > len(candidates):
        raise ValueError(
            f"기존 카테고리 {seed_count}개가 필요하지만 사용 가능한 카테고리는 "
            f"{len(candidates)}개입니다."
        )
    if seed_count in PRESET_SEEDS:
        return [dict(item) for item in PRESET_SEEDS[seed_count]]
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
