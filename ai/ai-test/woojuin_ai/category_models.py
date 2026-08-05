"""증분 카테고리(핵심 대상/앵커) 엔진 — stateless decide API 모델.

AI 서버는 상태를 저장하지 않는다. 백엔드가 전달한 현재 워크스페이스 상태(정식 카테고리,
후보 shortlist, 잠정 신호)를 입력받아 판단만 하고, 백엔드가 적용해야 할 actions만 반환한다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from .models import StrictModel

AnchorType = Literal["ENTITY", "UMBRELLA_TOPIC", "OTHER"]
FormalOrigin = Literal["SEED", "AI_PROMOTED"]
ActionType = Literal[
    "LINK_FORMAL_CATEGORY",
    "STORE_SIGNAL",
    "CREATE_CANDIDATE",
    "LINK_CANDIDATE",
    "PROMOTE_CANDIDATE",
]
MatchType = Literal["PROMOTED_FORMAL", "CANDIDATE", "SIGNAL", "NONE"]
MatchMethod = Literal["ENTITY_EXACT", "ENTITY_ALIAS", "EMBEDDING", "AI_REVIEW"]


# ---- 입력 ----


class DecideItem(StrictModel):
    item_id: int = Field(gt=0)
    type: Literal["URL", "MEMO", "IMAGE"] = "URL"
    title: str | None = Field(default=None, max_length=1_000)
    summary: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def has_text(self) -> "DecideItem":
        if not (self.title or self.summary):
            raise ValueError("title, summary 중 하나는 필요합니다")
        return self


class DecideFormalCategory(StrictModel):
    category_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)
    origin: FormalOrigin = "SEED"
    anchor_type: AnchorType | None = None
    normalized_anchor_name: str | None = Field(default=None, max_length=100)
    aliases: list[str] = Field(default_factory=list, max_length=50)


class ItemSample(StrictModel):
    title: str | None = Field(default=None, max_length=300)
    summary: str | None = Field(default=None, max_length=2_000)


class DecideCandidate(StrictModel):
    candidate_id: int = Field(gt=0)
    suggested_name: str = Field(min_length=1, max_length=100)
    anchor_type: AnchorType | None = None
    normalized_anchor_name: str | None = Field(default=None, max_length=100)
    aliases: list[str] = Field(default_factory=list, max_length=50)
    support_count: int = Field(ge=0)
    # 백엔드가 임베딩 Top-K로 좁힐 때의 유사도(선택). AI는 저장하지 않고 참고만.
    similarity: float | None = Field(default=None, ge=-1, le=1)
    representative_items: list[ItemSample] = Field(default_factory=list, max_length=10)


class DecideSignal(StrictModel):
    signal_id: int | None = Field(default=None, gt=0)
    first_item_id: int | None = Field(default=None, gt=0)
    anchor_type: AnchorType | None = None
    normalized_anchor_name: str | None = Field(default=None, max_length=100)
    aliases: list[str] = Field(default_factory=list, max_length=50)
    first_item: ItemSample = Field(default_factory=ItemSample)
    similarity: float | None = Field(default=None, ge=-1, le=1)


class DecideInput(StrictModel):
    workspace_id: int = Field(gt=0)
    item: DecideItem
    formal_categories: list[DecideFormalCategory] = Field(min_length=1, max_length=20)
    candidate_shortlist: list[DecideCandidate] = Field(default_factory=list, max_length=20)
    provisional_signal: DecideSignal | None = None

    @field_validator("formal_categories")
    @classmethod
    def unique_formal_ids(cls, values: list[DecideFormalCategory]) -> list[DecideFormalCategory]:
        ids = [v.category_id for v in values]
        if len(set(ids)) != len(ids):
            raise ValueError("formalCategories의 categoryId는 중복될 수 없습니다")
        return values


# ---- 출력 ----


class CategoryAnchorOut(StrictModel):
    name: str
    normalized_name: str
    type: AnchorType
    aliases: list[str] = Field(default_factory=list)
    specific_entities: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class MatchOut(StrictModel):
    type: MatchType
    target_id: int | None = None
    method: MatchMethod | None = None


class Action(StrictModel):
    """백엔드가 DB·Redis에 적용할 상태 변경 명령. type별로 필요한 필드만 채운다."""

    type: ActionType
    category_id: int | None = None
    candidate_id: int | None = None
    support_count_after: int | None = None
    suggested_name: str | None = None
    anchor_type: AnchorType | None = None
    normalized_anchor_name: str | None = None
    aliases: list[str] | None = None
    link_item_ids: list[int] | None = None
    category_name: str | None = None
    reason: str | None = None


class DecideOutput(StrictModel):
    workspace_id: int
    item_id: int
    formal_category_ids: list[int]
    ambiguous: bool
    category_anchor: CategoryAnchorOut
    match: MatchOut
    actions: list[Action]


# ---- AI 원시 응답(모델 계약 검증용) ----


class RawFormalScore(StrictModel):
    category_id: int
    score: float = Field(ge=0, le=1)


class RawFormalScores(StrictModel):
    scores: list[RawFormalScore] = Field(min_length=1, max_length=20)


class RawAnchor(StrictModel):
    category_anchor_name: str = Field(max_length=100)
    category_anchor_type: AnchorType
    normalized_anchor_name: str = Field(max_length=100)
    specific_entities: list[str] = Field(default_factory=list, max_length=20)
    aliases: list[str] = Field(default_factory=list, max_length=20)
    anchor_confidence: float = Field(ge=0, le=1)
    anchor_evidence: str = Field(default="", max_length=300)


class RawReuseDecision(StrictModel):
    action: Literal["REUSE", "CREATE", "SKIP"]
    candidate_id: int | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)
    reason: str = Field(default="", max_length=300)


class RawConvertDecision(StrictModel):
    convert: bool
    confidence: float = Field(default=0.0, ge=0, le=1)
    reason: str = Field(default="", max_length=300)


class RawPromoteDecision(StrictModel):
    promote: bool
    reason: str = Field(default="", max_length=300)
