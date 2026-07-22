import json
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

class IntegratedResult(SummaryResult, MetadataResult):
    category: str

MODELS: dict[str, type[BaseModel]] = {
    "category-only": CategoryResult,
    "summary-only": SummaryResult,
    "metadata-only": MetadataResult,
    "integrated": IntegratedResult,
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
