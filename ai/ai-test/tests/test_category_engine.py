"""stateless category-engine decide 테스트.

OpenRouter 호출을 통제하는 FakeClient로 decide 판단 로직만 검증한다.
decide는 임베딩을 호출하지 않아야 한다(백엔드가 Top-K로 후보를 좁혀 전달).
"""

from __future__ import annotations

import pytest

from woojuin_ai.category_models import (
    DecideCandidate,
    DecideFormalCategory,
    DecideInput,
    DecideItem,
    DecideSignal,
    ItemSample,
)
from woojuin_ai.category_service import CategoryEngineService
from woojuin_ai.config import Settings


class FakeClient:
    def __init__(self, *, formal, anchor, reuse=None, convert=None, promote=None):
        self.formal = formal
        self.anchor = anchor
        self.reuse = reuse
        self.convert = convert
        self.promote = promote
        self.calls: list[str] = []

    def chat_json(self, *, messages, schema, schema_name):
        self.calls.append(schema_name)
        mapping = {
            "formal_classification": self.formal,
            "category_anchor": self.anchor,
            "candidate_entry_review": self.reuse,
            "signal_conversion_review": self.convert,
            "promotion_review": self.promote,
        }
        result = mapping.get(schema_name)
        assert result is not None, f"준비되지 않은 호출: {schema_name}"
        return result

    def create_embeddings(self, texts):  # pragma: no cover - 호출되면 실패
        raise AssertionError("decide는 임베딩을 호출하지 않아야 합니다")


def settings() -> Settings:
    return Settings(api_key="test", category_min_support_count=3, anchor_min_confidence=0.5)


def formal_scores(top_id: int) -> dict:
    return {"scores": [{"categoryId": top_id, "score": 0.95}, {"categoryId": 99, "score": 0.1}]}


def anchor(name, atype="ENTITY", conf=0.95, aliases=None, normalized=None):
    return {
        "categoryAnchorName": name,
        "categoryAnchorType": atype,
        "normalizedAnchorName": normalized or name,
        "specificEntities": [],
        "aliases": aliases or [],
        "anchorConfidence": conf,
        "anchorEvidence": "test",
    }


SEED = DecideFormalCategory(category_id=1, name="학습·커리어", origin="SEED")
SEED2 = DecideFormalCategory(category_id=99, name="생활·건강", origin="SEED")


def decide(client, **kw):
    service = CategoryEngineService(client, settings())
    item = kw.pop("item", DecideItem(item_id=123, title="테스트", summary="요약"))
    formals = kw.pop("formals", [SEED, SEED2])
    return service.decide(
        DecideInput(workspace_id=10, item=item, formal_categories=formals, **kw)
    )


def action_types(out) -> list[str]:
    return [a.type for a in out.actions]


def test_promoted_formal_reuse():
    promoted = DecideFormalCategory(
        category_id=7, name="SSAFY", origin="AI_PROMOTED",
        anchor_type="ENTITY", normalized_anchor_name="ssafy", aliases=["싸피"],
    )
    client = FakeClient(formal=formal_scores(1), anchor=anchor("SSAFY", normalized="ssafy"))
    out = decide(client, formals=[SEED, SEED2, promoted])
    assert out.match.type == "PROMOTED_FORMAL"
    assert out.match.target_id == 7
    assert out.formal_category_ids == [1, 7]
    assert action_types(out) == ["LINK_FORMAL_CATEGORY", "LINK_FORMAL_CATEGORY"]
    # 승격 카테고리 재사용은 AI 승격/신호 호출 없이 끝난다
    assert client.calls == ["formal_classification", "category_anchor"]


def test_candidate_link_entity_rule_promotion():
    cand = DecideCandidate(
        candidate_id=5, suggested_name="짱구", anchor_type="ENTITY",
        normalized_anchor_name="짱구", aliases=[], support_count=2,
    )
    client = FakeClient(formal=formal_scores(1), anchor=anchor("짱구"))
    out = decide(client, candidate_shortlist=[cand])
    assert out.match.type == "CANDIDATE"
    assert out.match.method == "ENTITY_EXACT"
    types = action_types(out)
    assert "LINK_CANDIDATE" in types
    assert "PROMOTE_CANDIDATE" in types  # ENTITY 3건 → 규칙 기반 승격
    link = next(a for a in out.actions if a.type == "LINK_CANDIDATE")
    assert link.support_count_after == 3
    # 규칙 기반이므로 AI 승격 검토를 호출하지 않는다
    assert "promotion_review" not in client.calls


def test_umbrella_uses_ai_promotion_reject():
    cand = DecideCandidate(
        candidate_id=8, suggested_name="운세", anchor_type="UMBRELLA_TOPIC",
        normalized_anchor_name="운세", aliases=[], support_count=2,
        representative_items=[ItemSample(title="별자리 운세"), ItemSample(title="타로")],
    )
    client = FakeClient(
        formal=formal_scores(1), anchor=anchor("운세", atype="UMBRELLA_TOPIC"),
        promote={"promote": False, "reason": "너무 넓음"},
    )
    out = decide(client, candidate_shortlist=[cand])
    assert "LINK_CANDIDATE" in action_types(out)
    assert "PROMOTE_CANDIDATE" not in action_types(out)  # AI가 거부
    assert "promotion_review" in client.calls


def test_umbrella_ai_promotion_accept():
    cand = DecideCandidate(
        candidate_id=8, suggested_name="운세", anchor_type="UMBRELLA_TOPIC",
        normalized_anchor_name="운세", aliases=[], support_count=2,
    )
    client = FakeClient(
        formal=formal_scores(1), anchor=anchor("운세", atype="UMBRELLA_TOPIC"),
        promote={"promote": True, "reason": "일관됨"},
    )
    out = decide(client, candidate_shortlist=[cand])
    assert "PROMOTE_CANDIDATE" in action_types(out)


def test_signal_conversion_by_anchor():
    sig = DecideSignal(
        signal_id=3, first_item_id=100, anchor_type="ENTITY",
        normalized_anchor_name="짱구", aliases=[], first_item=ItemSample(title="맹구"),
    )
    client = FakeClient(formal=formal_scores(1), anchor=anchor("짱구"))
    out = decide(client, provisional_signal=sig)
    assert out.match.type == "SIGNAL"
    create = next(a for a in out.actions if a.type == "CREATE_CANDIDATE")
    assert create.support_count_after == 2
    assert set(create.link_item_ids) == {100, 123}
    # 앵커 권위 전환은 AI 신호검토 없이 끝난다
    assert "signal_conversion_review" not in client.calls


def test_deferred_store_signal_when_no_match():
    client = FakeClient(formal=formal_scores(1), anchor=anchor("새로운대상"))
    out = decide(client)  # 후보/신호 없음
    assert out.match.type == "NONE"
    store = next(a for a in out.actions if a.type == "STORE_SIGNAL")
    assert store.normalized_anchor_name == "새로운대상"
    assert store.link_item_ids == [123]


def test_low_confidence_anchor_requires_ai_review():
    cand = DecideCandidate(
        candidate_id=9, suggested_name="세부주제", anchor_type=None,
        normalized_anchor_name=None, aliases=[], support_count=1, similarity=0.4,
    )
    client = FakeClient(
        formal=formal_scores(1),
        anchor=anchor("불명확", atype="OTHER", conf=0.2),  # 저신뢰 → 권위 매칭 안 씀
        reuse={"action": "REUSE", "candidateId": 9, "confidence": 0.7, "reason": "같은 주제"},
    )
    out = decide(client, candidate_shortlist=[cand])
    assert out.match.type == "CANDIDATE"
    assert out.match.method == "AI_REVIEW"  # 임베딩만으로 전환 안 하고 AI 검증
    assert "candidate_entry_review" in client.calls
