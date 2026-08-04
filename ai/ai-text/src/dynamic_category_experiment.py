from __future__ import annotations

import hashlib
import json
import random
import re
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
    # 생성 카테고리를 다음 데이터의 후보로 누적하는 공정 비교 조건
    "ai-only-cumulative": DynamicCategoryScenario(
        "ai-only-cumulative", "기존 카테고리 없음 + AI 생성 누적", 0, accumulate=True
    ),
    "existing3-ai-cumulative": DynamicCategoryScenario(
        "existing3-ai-cumulative", "기존 3개 + AI 생성 누적", 3, accumulate=True
    ),
    "existing5-ai-cumulative": DynamicCategoryScenario(
        "existing5-ai-cumulative", "기존 5개 + AI 생성 누적", 5, accumulate=True
    ),
    "existing7-ai-cumulative": DynamicCategoryScenario(
        "existing7-ai-cumulative", "기존 7개 + AI 생성 누적", 7, accumulate=True
    ),
    "existing11-ai-cumulative": DynamicCategoryScenario(
        "existing11-ai-cumulative", "기존 11개 + AI 생성 누적", 11, accumulate=True
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

# 목표 비교 조건: AI 생성 전용 / 기존 5개 / 기존 7개를 동일 누적 방식으로 실행
CUMULATIVE_COMPARE = (
    "ai-only-cumulative",
    "existing5-ai-cumulative",
    "existing7-ai-cumulative",
)

# 데이터 순서 실험: 이름 -> 셔플 시드(None이면 원본 순서)
ORDERINGS: dict[str, int | None] = {
    "original": None,
    "shuffle-42": 42,
    "shuffle-84": 84,
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
        elif value in {"cumulative-compare", "cumulative-ai", "cumulative-reduced"}:
            expanded.extend(CUMULATIVE_COMPARE)
        elif value == "reduced-ai-cumulative":
            expanded.extend(
                (
                    "existing3-ai-cumulative",
                    "existing5-ai-cumulative",
                    "existing7-ai-cumulative",
                )
            )
        elif value in SCENARIOS:
            expanded.append(value)
        else:
            raise ValueError(f"지원하지 않는 시나리오: {value}")
    return [SCENARIOS[value] for value in dict.fromkeys(expanded)]


def resolve_orderings(values: Iterable[str]) -> list[str]:
    requested = [str(value).strip().lower() for value in values if str(value).strip()]
    if not requested:
        return ["original"]
    expanded: list[str] = []
    for value in requested:
        if value == "all":
            expanded.extend(ORDERINGS)
        elif value in ORDERINGS:
            expanded.append(value)
        else:
            raise ValueError(
                f"지원하지 않는 데이터 순서: {value} (사용 가능: {', '.join(ORDERINGS)})"
            )
    return list(dict.fromkeys(expanded))


def apply_ordering(
    data: list[dict[str, Any]], order_name: str
) -> tuple[list[dict[str, Any]], int | None]:
    """데이터 순서를 결정론적으로 적용한다. shuffle은 고정 시드를 사용한다."""
    if order_name not in ORDERINGS:
        raise ValueError(f"지원하지 않는 데이터 순서: {order_name}")
    seed = ORDERINGS[order_name]
    ordered = list(data)
    if seed is not None:
        random.Random(seed).shuffle(ordered)
    return ordered, seed


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


# 이름 정규화에 사용하는 구분자 문자 집합
_SEPARATOR_CHARS = "·/|,&"
_SEPARATOR_PATTERN = re.compile(rf"\s*([{re.escape(_SEPARATOR_CHARS)}])\s*")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_TOKEN_SPLIT_PATTERN = re.compile(rf"[{re.escape(_SEPARATOR_CHARS)}\s\-]+")

GENERATED_ORIGINS = {"GENERATED", "AI_GENERATED"}


def normalize_category_name(name: str) -> str:
    """앞뒤 공백 제거, 연속 공백 축소, 구분자 앞뒤 공백 정리를 적용한다.

    대소문자와 의미는 바꾸지 않는다. 완전히 동일한 이름만 같은 것으로 취급하기 위한 표기 정규화다.
    """
    text = _WHITESPACE_PATTERN.sub(" ", str(name).strip())
    text = _SEPARATOR_PATTERN.sub(r"\1", text)
    return text.strip()


def category_key(name: str) -> str:
    """중복 판단용 키. 표기 정규화 후 영문 대소문자 차이를 무시한다."""
    return normalize_category_name(name).casefold()


def name_tokens(name: str) -> set[str]:
    """구분자·공백·하이픈으로 나눈 핵심 토큰 집합(소문자)."""
    normalized = normalize_category_name(name).casefold()
    return {token for token in _TOKEN_SPLIT_PATTERN.split(normalized) if token}


def is_generated_origin(origin: Any) -> bool:
    return str(origin).upper() in GENERATED_ORIGINS


def format_catalog(definitions: list[dict[str, Any]]) -> str:
    if not definitions:
        return "- 없음 (반드시 새 카테고리를 생성하세요)"
    lines = []
    for item in definitions:
        origin = "AI 생성" if is_generated_origin(item.get("origin")) else "기존"
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
    digest = hashlib.sha1(category_key(name).encode("utf-8")).hexdigest()[:10]
    return f"AI-{digest.upper()}"


class CategoryCatalog:
    """시드(SEED) 카테고리와 AI 생성(GENERATED) 카테고리를 함께 관리한다.

    - 시드 카테고리는 origin="SEED", createdAtItemId=None.
    - 생성 카테고리는 origin="GENERATED", createdAtItemId=최초 생성 데이터 ID.
    - 표기 정규화 후 완전히 동일한 이름은 새로 추가하지 않는다(의미 병합은 하지 않음).
    """

    def __init__(self, definitions: list[dict[str, Any]]) -> None:
        self._definitions: list[dict[str, Any]] = []
        for item in definitions:
            normalized = dict(item)
            origin = str(normalized.get("origin") or "SEED").upper()
            normalized["origin"] = "GENERATED" if is_generated_origin(origin) else "SEED"
            normalized.setdefault("createdAtItemId", None)
            self._append(normalized)

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._definitions]

    def find(self, name: str) -> dict[str, Any] | None:
        key = category_key(name)
        return next(
            (dict(item) for item in self._definitions if category_key(item["name"]) == key),
            None,
        )

    def add_generated(
        self,
        name: str,
        description: str,
        created_at_item_id: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        existing = self.find(name)
        if existing is not None:
            return existing, False
        clean_name = normalize_category_name(name)
        item = {
            "id": generated_category_id(clean_name),
            "name": clean_name,
            "description": description.strip(),
            "examples": [],
            "origin": "GENERATED",
            "createdAtItemId": created_at_item_id,
        }
        self._append(item)
        return dict(item), True

    def _append(self, item: dict[str, Any]) -> None:
        name = normalize_category_name(item.get("name", ""))
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
        category_key(str(item["name"])): item for item in available_definitions
    }
    matched = by_name.get(category_key(values["categoryName"]))
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


# 데이터별 선택 결과 구분
SEED_EXISTING = "SEED_EXISTING"
GENERATED_EXISTING = "GENERATED_EXISTING"
NEW_GENERATED = "NEW_GENERATED"


def classify_selection(
    parsed: dict[str, Any],
    available_definitions: list[dict[str, Any]],
    result_catalog: CategoryCatalog,
    item_id: str,
) -> tuple[dict[str, Any], str, bool]:
    """모델 응답을 선택 유형으로 분류하고 필요하면 결과 카탈로그에 카테고리를 추가한다.

    반환: (선택된 카테고리 정의, selectionType, 이번 데이터에서 새 카테고리를 만들었는지)
    - SEED_EXISTING: 처음 제공된 시드 카테고리 선택
    - GENERATED_EXISTING: 앞에서 AI가 생성한 카테고리 재사용
    - NEW_GENERATED: 새로운 카테고리 생성
    available_definitions는 이 데이터를 처리할 때 프롬프트로 제공된 후보 목록이다.
    """
    available_by_key = {
        category_key(str(item["name"])): item for item in available_definitions
    }
    name = parsed["categoryName"]
    origin = str(parsed.get("categoryOrigin", "")).upper()

    if origin == "EXISTING":
        prompt_category = available_by_key.get(category_key(name))
        # parse 단계에서 EXISTING은 제공된 이름과 일치함이 보장된다.
        selected = result_catalog.find(name) or dict(prompt_category or {})
        selection_type = (
            GENERATED_EXISTING
            if is_generated_origin((prompt_category or selected).get("origin"))
            else SEED_EXISTING
        )
        return selected, selection_type, False

    # origin == GENERATED (parse 단계에서 시드/제공 후보와 겹치지 않음이 확인됨)
    selected, created = result_catalog.add_generated(
        name, parsed.get("categoryDescription", ""), item_id
    )
    if created:
        return selected, NEW_GENERATED, True
    # 비누적 조건에서 서로 다른 데이터가 같은 이름을 동시에 생성해 충돌한 경우.
    # 이 데이터의 프롬프트에는 없던 이름이므로 재사용이 아닌 신규 생성으로 집계한다.
    return selected, NEW_GENERATED, False


def find_duplicate_candidates(
    categories: list[dict[str, Any]], *, min_jaccard: float = 0.5
) -> list[dict[str, Any]]:
    """이름 토큰이 비슷한 생성 카테고리 쌍을 검토 후보로 기록한다(자동 병합하지 않음)."""
    generated = [item for item in categories if is_generated_origin(item.get("origin"))]
    candidates: list[dict[str, Any]] = []
    for first in range(len(generated)):
        for second in range(first + 1, len(generated)):
            left, right = generated[first], generated[second]
            left_tokens, right_tokens = name_tokens(left["name"]), name_tokens(right["name"])
            if not left_tokens or not right_tokens:
                continue
            shared = left_tokens & right_tokens
            union = left_tokens | right_tokens
            jaccard = len(shared) / len(union) if union else 0.0
            if left_tokens == right_tokens:
                reason = "이름에 포함된 핵심 단어가 동일함"
            elif left_tokens <= right_tokens or right_tokens <= left_tokens:
                reason = "한 이름의 핵심 단어가 다른 이름에 모두 포함됨"
            elif jaccard >= min_jaccard:
                reason = f"핵심 단어를 다수 공유함 (Jaccard {jaccard:.2f})"
            else:
                continue
            candidates.append(
                {
                    "categories": [left["name"], right["name"]],
                    "categoryIds": [left.get("id"), right.get("id")],
                    "sharedTokens": sorted(shared),
                    "jaccard": round(jaccard, 4),
                    "reason": reason,
                }
            )
    return candidates
