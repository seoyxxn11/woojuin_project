import json
import math
import re
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator

def sentence_count(text: str) -> int:
    parts = [x for x in re.split(r"(?<=[.!?。！？])\s*|\n+", text.strip()) if x.strip()]
    return len(parts) or (1 if text.strip() else 0)

class StrictResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

class CategoryResult(StrictResult):
    category: str
    confidence: float = Field(ge=0, le=1)

    @field_validator("confidence", mode="before")
    @classmethod
    def confidence_is_number(cls, value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("confidence는 숫자여야 합니다")
        return value

class SummaryResult(StrictResult):
    summary: str = Field(min_length=1)

    @field_validator("summary")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip(): raise ValueError("빈 문자열은 허용되지 않습니다")
        return value

    @field_validator("summary")
    @classmethod
    def summary_sentences(cls, value: str) -> str:
        if not 1 <= sentence_count(value) <= 3: raise ValueError("요약은 1~3문장이어야 합니다")
        return value

class MetadataResult(StrictResult):
    tags: list[str] = Field(min_length=3, max_length=5)
    keywords: list[str] = Field(min_length=3, max_length=5)

    @field_validator("tags", "keywords")
    @classmethod
    def valid_terms(cls, values: list[str]) -> list[str]:
        if any(not isinstance(v, str) or not v.strip() for v in values): raise ValueError("빈 항목은 허용되지 않습니다")
        normalized = [v.strip().casefold() for v in values]
        if len(normalized) != len(set(normalized)): raise ValueError("중복 항목은 허용되지 않습니다")
        return values

class OrganizeResult(SummaryResult, MetadataResult):
    pass

class IntegratedResult(OrganizeResult):
    category: str

class CategoryScoreResult(StrictResult):
    categoryId: str
    categoryName: str
    score: float = Field(ge=0, le=1)

class MultiCategoryResult(StrictResult):
    categories: list[CategoryScoreResult]

class MultiIntegratedResult(OrganizeResult):
    categories: list[CategoryScoreResult]

MODELS: dict[str, type[BaseModel]] = {
    "category-only": CategoryResult,
    "summary-only": SummaryResult,
    "metadata-only": MetadataResult,
    "organize-only": OrganizeResult,
    "integrated": IntegratedResult,
    "multi-category": MultiCategoryResult,
    "multi-integrated": MultiIntegratedResult,
}

def _balanced_json(text: str) -> tuple[str | None, tuple[int, int] | None]:
    for start, ch in enumerate(text):
        if ch != "{": continue
        depth, quoted, escaped = 0, False, False
        for i in range(start, len(text)):
            c = text[i]
            if quoted:
                if escaped: escaped = False
                elif c == "\\": escaped = True
                elif c == '"': quoted = False
            elif c == '"': quoted = True
            elif c == "{": depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0: return text[start:i+1], (start, i+1)
    return None, None

def output_schema(categories: list[str], mode: str = "integrated") -> dict[str, Any]:
    if mode not in MODELS: raise ValueError(f"지원하지 않는 테스트 모드: {mode}")
    schema = MODELS[mode].model_json_schema()
    if "category" in schema["properties"]:
        schema["properties"]["category"]["enum"] = categories
    if mode in {"multi-category", "multi-integrated"}:
        item_schema = schema.get("$defs", {}).get("CategoryScoreResult", {}).get("properties", {})
        if "categoryName" in item_schema:
            item_schema["categoryName"]["enum"] = categories
    return schema


def output_multi_label_schema(definitions: list[dict[str, Any]], integrated: bool = False) -> dict[str, Any]:
    schema = output_schema([str(item["name"]) for item in definitions], "multi-integrated" if integrated else "multi-category")
    item_schema = schema.get("$defs", {}).get("CategoryScoreResult", {}).get("properties", {})
    if "categoryId" in item_schema:
        item_schema["categoryId"]["enum"] = [str(item["id"]) for item in definitions]
    return schema

def parse_response(raw: str, categories: list[str], mode: str = "integrated") -> dict[str, Any]:
    if mode not in MODELS: raise ValueError(f"지원하지 않는 테스트 모드: {mode}")
    thinking = bool(re.search(r"<think>.*?</think>", raw, flags=re.S | re.I))
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.S | re.I).strip()
    candidate, span = _balanced_json(cleaned)
    extra = candidate is not None and bool(cleaned[:span[0]].strip() or cleaned[span[1]:].strip())
    result: dict[str, Any] = {"rawResponse": raw, "thinkingTagDetected": thinking, "extraTextDetected": extra, "jsonValid": False, "schemaValid": False, "requiredFieldsPresent": False, "parsedResponse": None, "validationError": ""}
    if not candidate:
        result["validationError"] = "JSON 객체를 찾지 못했습니다"; return result
    try:
        parsed = json.loads(candidate)
        required = set(MODELS[mode].model_fields)
        result.update(jsonValid=True, parsedResponse=parsed, requiredFieldsPresent=all(k in parsed for k in required))
        validated = MODELS[mode].model_validate(parsed)
        category = getattr(validated, "category", None)
        if category is not None and category not in categories:
            raise ValueError(f"허용되지 않은 카테고리: {category}")
        result.update(schemaValid=True, parsedResponse=validated.model_dump())
    except (json.JSONDecodeError, ValueError) as exc:
        result["validationError"] = str(exc)
    return result


def parse_multi_label_response(
    raw: str,
    definitions: list[dict[str, Any]],
    *,
    integrated: bool = False,
) -> dict[str, Any]:
    """다중 카테고리 응답을 보존하면서 평가 가능한 후보와 오류를 분리한다."""
    thinking = bool(re.search(r"<think>.*?</think>", raw, flags=re.S | re.I))
    markdown = bool(re.search(r"```(?:json)?\s*.*?```", raw, flags=re.S | re.I))
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.S | re.I).strip()
    candidate, span = _balanced_json(cleaned)
    extra = candidate is not None and bool(cleaned[:span[0]].strip() or cleaned[span[1]:].strip())
    result: dict[str, Any] = {
        "rawResponse": raw,
        "thinkingTagDetected": thinking,
        "markdownCodeBlockDetected": markdown,
        "extraTextDetected": extra,
        "jsonValid": False,
        "schemaValid": False,
        "requiredFieldsPresent": False,
        "categoryParseSuccess": False,
        "summaryParseSuccess": None if not integrated else False,
        "organizationParseSuccess": None if not integrated else False,
        "legacySingleCategory": False,
        "legacyCategoryIgnored": False,
        "singleObjectNormalized": False,
        "rawPredictions": [],
        "validPredictions": [],
        "invalidPredictions": [],
        "duplicateCategoryIds": [],
        "parsedResponse": None,
        "validationError": "",
    }
    if not candidate:
        result["validationError"] = "JSON 객체를 찾지 못했습니다"
        return result
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        result["validationError"] = str(exc)
        return result
    if not isinstance(parsed, dict):
        result["validationError"] = "최상위 JSON은 객체여야 합니다"
        return result
    result["jsonValid"] = True

    entries: list[Any]
    if "categories" in parsed:
        category_value = parsed["categories"]
        if isinstance(category_value, dict):
            entries = [category_value]
            result["singleObjectNormalized"] = True
        elif isinstance(category_value, list):
            entries = category_value
        else:
            entries = []
            result["invalidPredictions"].append(_invalid("INVALID_CATEGORY", category_value, "categories는 배열 또는 객체여야 합니다"))
        result["requiredFieldsPresent"] = True
        if "category" in parsed:
            result["legacyCategoryIgnored"] = True
    elif "category" in parsed:
        entries = [{
            "categoryName": parsed.get("category"),
            "score": parsed.get("score", parsed.get("confidence")),
        }]
        result["legacySingleCategory"] = True
        result["requiredFieldsPresent"] = True
    else:
        entries = []
        result["validationError"] = "categories 또는 기존 category 필드가 필요합니다"

    result["rawPredictions"] = entries
    by_id = {str(item["id"]): item for item in definitions}
    by_name = {str(item["name"]): item for item in definitions}
    valid_by_id: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()
    for position, entry in enumerate(entries):
        normalized, errors = _normalize_prediction(entry, position, by_id, by_name)
        result["invalidPredictions"].extend(errors)
        if normalized is None:
            continue
        category_id = normalized["categoryId"]
        if category_id in valid_by_id:
            duplicates.add(category_id)
            if normalized["score"] > valid_by_id[category_id]["score"]:
                valid_by_id[category_id] = normalized
        else:
            valid_by_id[category_id] = normalized
    result["duplicateCategoryIds"] = sorted(duplicates)
    result["validPredictions"] = sorted(
        valid_by_id.values(), key=lambda item: float(item["score"]), reverse=True
    )
    result["categoryParseSuccess"] = not result["invalidPredictions"] and result["requiredFieldsPresent"]

    summary = parsed.get("summary")
    tags = parsed.get("tags")
    keywords = parsed.get("keywords")
    if integrated:
        summary_valid = isinstance(summary, str) and bool(summary.strip()) and 1 <= sentence_count(summary) <= 3
        tags_valid = _valid_terms(tags)
        keywords_valid = _valid_terms(keywords)
        result["summaryParseSuccess"] = summary_valid
        result["organizationParseSuccess"] = summary_valid and tags_valid and keywords_valid

    parsed_response: dict[str, Any] = {"categories": result["validPredictions"]}
    if integrated:
        parsed_response.update({"summary": summary, "tags": tags, "keywords": keywords})
    result["parsedResponse"] = parsed_response
    result["schemaValid"] = bool(
        result["categoryParseSuccess"]
        and (not integrated or result["organizationParseSuccess"])
    )
    errors = [str(item["errorType"]) for item in result["invalidPredictions"]]
    if errors:
        result["validationError"] = " | ".join(dict.fromkeys(errors))
    return result


def _normalize_prediction(
    entry: Any,
    position: int,
    by_id: dict[str, dict[str, Any]],
    by_name: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not isinstance(entry, dict):
        return None, [_invalid("INVALID_CATEGORY", entry, "카테고리 항목은 객체여야 합니다", position)]
    raw_id = str(entry.get("categoryId", "")).strip()
    raw_name = str(entry.get("categoryName", entry.get("category", ""))).strip()
    definition: dict[str, Any] | None = None
    errors: list[dict[str, Any]] = []
    if raw_id:
        definition = by_id.get(raw_id)
        if definition is None:
            errors.append(_invalid("INVALID_CATEGORY", entry, f"존재하지 않는 categoryId: {raw_id}", position))
        elif raw_name and raw_name != str(definition["name"]):
            errors.append(_invalid(
                "CATEGORY_ID_NAME_MISMATCH", entry,
                f"{raw_id}의 이름은 {definition['name']}이어야 합니다", position,
            ))
    elif raw_name:
        definition = by_name.get(raw_name)
        if definition is None:
            errors.append(_invalid("INVALID_CATEGORY", entry, f"존재하지 않는 categoryName: {raw_name}", position))
    else:
        errors.append(_invalid("INVALID_CATEGORY", entry, "categoryId 또는 categoryName이 필요합니다", position))

    score = entry.get("score", entry.get("confidence"))
    if score is None or score == "":
        errors.append(_invalid("SCORE_MISSING", entry, "score가 필요합니다", position))
    elif isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(float(score)):
        errors.append(_invalid("SCORE_PARSE_ERROR", entry, "score는 유한한 숫자여야 합니다", position))
    elif not 0 <= float(score) <= 1:
        errors.append(_invalid("SCORE_OUT_OF_RANGE", entry, "score는 0 이상 1 이하여야 합니다", position))
    if errors or definition is None:
        return None, errors
    return {
        "categoryId": str(definition["id"]),
        "categoryName": str(definition["name"]),
        "score": float(score),
    }, []


def _invalid(error_type: str, raw: Any, message: str, position: int | None = None) -> dict[str, Any]:
    return {"errorType": error_type, "message": message, "position": position, "raw": raw}


def _valid_terms(value: Any) -> bool:
    if not isinstance(value, list) or not 3 <= len(value) <= 5:
        return False
    normalized = [str(item).strip().casefold() for item in value if isinstance(item, str)]
    return len(normalized) == len(value) and all(normalized) and len(normalized) == len(set(normalized))
