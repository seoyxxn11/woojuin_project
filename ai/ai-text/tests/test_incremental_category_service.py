"""증분 카테고리 서비스 엔진 테스트.

정식 분류 점수·임베딩·후보 이름 생성·승격 검토를 완전히 통제하는 FakeBackend로
엔진 로직만 결정론적으로 검증한다. (실제 임베딩/모델 품질은 별도 실행에서 확인)
"""

from __future__ import annotations

import hashlib
import itertools
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest

from src.incremental_category_service import (
    CANDIDATE_LINKED,
    FORMAL_ONLY,
    MERGED,
    PENDING,
    PROMOTED,
    READY_TO_PROMOTE,
    ServiceConfig,
    WorkspaceCategoryEngine,
    build_service_text,
    content_tokens,
    l2_normalize,
    summarize_run,
)

SEEDS = [
    {"id": f"S{i}", "name": f"시드{i}", "description": f"시드 카테고리 {i}", "examples": []}
    for i in range(1, 6)
]


class FakeBackend:
    """분류 점수·임베딩·후보 제안·승격 판정을 테스트에서 통제하는 백엔드."""

    def __init__(self, groups, *, scores=None, promote=True, fail_tokens=()):
        self.groups = list(groups)
        self.scores = scores or {}
        self.promote = promote
        self.fail_tokens = set(fail_tokens)
        self.dim = len(self.groups) + 8

    def embed(self, text: str):
        for token in self.fail_tokens:
            if token in text:
                raise RuntimeError(f"embed 실패: {token}")
        vector = [0.0] * self.dim
        matched = False
        for index, group in enumerate(self.groups):
            if group in text:
                vector[index] = 1.0
                matched = True
        if not matched:
            digest = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
            vector[len(self.groups) + digest % 8] = 1.0
        return l2_normalize(vector)

    def classify_formal(self, item, formal_categories):
        provided = dict(self.scores.get(item["testId"], []))
        return [
            {"categoryId": c["id"], "score": float(provided.get(c["id"], 0.2))}
            for c in formal_categories
        ]

    def propose_candidate(self, item, formal_categories, top_scores):
        return {
            "needsNew": True,
            "name": item.get("candidateName") or item["testId"],
            "description": "설명",
            "reason": "이유",
        }

    def review_promotion(self, candidate, linked_items):
        decision = self.promote(candidate) if callable(self.promote) else self.promote
        return {"promote": bool(decision), "reason": "테스트"}

    def review_candidate_entry(self, item, formal_category_name, candidate_infos, *, formal_confident):
        # 확신 분류면 일반 데이터로 보고 SKIP, 애매하면 새 세부주제로 CREATE
        if formal_confident:
            return {"action": "SKIP", "candidateId": None, "name": "", "description": "", "confidence": 0.6, "reason": "generic"}
        return {
            "action": "CREATE", "candidateId": None,
            "name": item.get("candidateName") or item["testId"], "description": "설명",
            "confidence": 0.8, "reason": "새 세부주제",
        }

    def review_signal_conversion(self, item, signal_info):
        return {"convert": True, "name": signal_info.get("suggestedName") or "세부주제",
                "description": "설명", "confidence": 0.9, "reason": "두 번째 유사 데이터"}

    def extract_core_entity(self, item):
        entity = item.get("entity")
        if entity:
            return dict(entity)
        return {
            "coreEntityName": "", "normalizedEntityName": "", "coreEntityType": "OTHER",
            "aliases": [], "entityConfidence": 0.0, "entityEvidence": "없음",
        }


def make_engine(backend, config=None, workspace_id=10):
    clock = itertools.count()
    base = datetime(2026, 8, 4, 13, 0, 0, tzinfo=timezone.utc)
    return WorkspaceCategoryEngine(
        workspace_id,
        SEEDS,
        backend,
        config or ServiceConfig(),
        now_fn=lambda: base.replace(microsecond=next(clock) % 1000),
    )


def item(test_id, group="", *, candidate_name=None, title=None, entity=None):
    text = f"{test_id} {group}"
    return {
        "testId": test_id,
        "title": title if title is not None else text,
        "inputType": "memo",
        "input": text,
        "candidateName": candidate_name,
        "entity": entity,
    }


def entity(name, *, etype="WORK", aliases=None, conf=0.9):
    return {
        "coreEntityName": name,
        "normalizedEntityName": name,
        "coreEntityType": etype,
        "aliases": list(aliases or []),
        "entityConfidence": conf,
        "entityEvidence": "테스트",
    }


# ---- 설정 ----


def test_config_from_mapping_supports_kebab_and_snake():
    config = ServiceConfig.from_mapping(
        {
            "max-count": 8,
            "candidate-min-support-count": 4,
            "formal_confidence_threshold": 0.7,
        }
    )
    assert config.max_count == 8
    assert config.candidate_min_support_count == 4
    assert config.formal_confidence_threshold == 0.7
    # 기본값 유지
    assert config.candidate_similarity_threshold == 0.80


# ---- 정식 분류 / 후보 ----


def test_clear_formal_classification_creates_no_candidate():
    backend = FakeBackend(groups=[], scores={"URL-001": [("S1", 0.9)]})
    engine = make_engine(backend)
    log = engine.submit_item(item("URL-001"))
    assert log["ambiguous"] is False
    assert log["selectedFormalCategoryId"] == "S1"
    assert log["linkedCandidateId"] is None
    assert engine.item_classifications["URL-001"].classificationStatus == FORMAL_ONLY
    assert engine.candidates == []


def test_ambiguous_item_creates_temporary_candidate_hidden_from_formal():
    backend = FakeBackend(groups=["grpA"])
    engine = make_engine(backend)
    log = engine.submit_item(item("URL-001", "grpA", candidate_name="운세·예측"))
    assert log["ambiguous"] is True
    assert log["newCandidateCreated"] is True
    # 데이터는 가장 가까운 정식 카테고리에 배치되고, 후보는 내부 연결로만 남는다.
    classification = engine.item_classifications["URL-001"]
    assert classification.formalCategoryId in {c["id"] for c in SEEDS}
    assert classification.classificationStatus == CANDIDATE_LINKED
    assert len(engine.candidates) == 1
    assert engine.candidates[0].suggestedName == "운세·예측"
    # 임시 후보는 정식 카테고리 목록(사용자 노출)에 들어가지 않는다.
    assert all(c["origin"] != "PROMOTED" for c in engine.formal_categories)
    assert len(engine.formal_categories) == 5


def test_similar_data_reuses_existing_candidate_no_duplicate():
    backend = FakeBackend(groups=["grpBIZ"])
    engine = make_engine(backend)
    # 이름 표현은 다르지만 같은 주제(임베딩 동일)의 세 데이터
    engine.submit_item(item("URL-001", "grpBIZ", candidate_name="사업·창업"))
    log2 = engine.submit_item(item("URL-002", "grpBIZ", candidate_name="창업·사업"))
    log3 = engine.submit_item(item("URL-003", "grpBIZ", candidate_name="온라인 창업"))
    assert log2["matchedExistingCandidate"] is True
    assert log3["matchedExistingCandidate"] is True
    # 중복 후보가 각각 생기지 않고 하나로 누적된다.
    active = [c for c in engine.candidates if c.status in {PENDING, READY_TO_PROMOTE, PROMOTED}]
    assert len(active) == 1
    assert active[0].supportCount == 3


def test_candidate_promotes_after_min_support_and_reclassifies():
    backend = FakeBackend(groups=["grpA"], promote=True)
    engine = make_engine(backend, ServiceConfig(candidate_min_support_count=3))
    logs = [
        engine.submit_item(item(f"URL-00{i}", "grpA", candidate_name="운세")) for i in range(1, 4)
    ]
    assert logs[-1]["promoted"] is True
    assert logs[-1]["reclassified"] is True
    # 새 정식 카테고리로 승격되고 연결 데이터가 재분류된다.
    promoted = [c for c in engine.formal_categories if c["origin"] == "PROMOTED"]
    assert len(promoted) == 1
    new_id = promoted[0]["id"]
    for i in range(1, 4):
        assert engine.item_classifications[f"URL-00{i}"].formalCategoryId == new_id
    assert len(engine.reclassified_item_ids) == 3
    assert engine.candidates[0].status == PROMOTED


def test_incoherent_candidate_is_held_when_review_rejects():
    backend = FakeBackend(groups=["grpApp"], promote=False)
    engine = make_engine(backend, ServiceConfig(candidate_min_support_count=3))
    for i in range(1, 4):
        engine.submit_item(item(f"URL-00{i}", "grpApp", candidate_name="앱 정보"))
    # 승격 검토에서 거부되면 정식 카테고리로 올라가지 않고 유지된다.
    assert engine.promoted_count() == 0
    assert len(engine.formal_categories) == 5
    assert engine.candidates[0].status == PENDING


def test_ready_to_promote_when_formal_categories_full():
    # 정식 최대 6개 → 시드 5 + 1개만 승격 가능
    config = ServiceConfig(candidate_min_support_count=3, max_count=6)
    backend = FakeBackend(groups=["grpA", "grpB"], promote=True)
    engine = make_engine(backend, config)
    for i in range(1, 4):
        engine.submit_item(item(f"A-{i}", "grpA", candidate_name="운세"))
    for i in range(1, 4):
        engine.submit_item(item(f"B-{i}", "grpB", candidate_name="심리"))
    assert len(engine.formal_categories) == 6
    assert engine.promoted_count() == 1
    statuses = {c.suggestedName: c.status for c in engine.candidates}
    assert statuses["운세"] == PROMOTED
    assert statuses["심리"] == READY_TO_PROMOTE
    assert summarize_run(engine)["exceededMaxFormalCategories"] is False


def test_candidate_failure_does_not_break_formal_classification():
    backend = FakeBackend(groups=["grpA"], fail_tokens=["FAILME"])
    engine = make_engine(backend)
    log = engine.submit_item(item("FAILME", "grpA"))
    # 후보 처리(임베딩)가 실패해도 데이터 저장과 정식 분류는 성공한다.
    assert log["candidateError"] is not None
    assert log["selectedFormalCategoryId"] in {c["id"] for c in SEEDS}
    assert "FAILME" in engine.item_classifications
    assert engine.item_classifications["FAILME"].classificationStatus == FORMAL_ONLY


def test_concurrent_submission_makes_single_candidate_no_double_count():
    backend = FakeBackend(groups=["grpA"], promote=False)
    engine = make_engine(backend, ServiceConfig(candidate_min_support_count=99))
    items = [item(f"URL-{i:03d}", "grpA", candidate_name="운세") for i in range(20)]
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(engine.submit_item, items))
    active = [c for c in engine.candidates if c.status != MERGED]
    # 동시에 들어와도 같은 의미 후보가 하나만 생기고 supportCount가 정확하다.
    assert len(active) == 1
    assert active[0].supportCount == 20
    assert len(active[0].linkedItemIds) == len(set(active[0].linkedItemIds))
    assert len(engine.formal_categories) <= engine.config.max_count


def test_manual_merge_marks_candidate_merged():
    backend = FakeBackend(groups=["grpA", "grpB"])
    engine = make_engine(backend)
    engine.submit_item(item("A-1", "grpA", candidate_name="창업·사업"))
    engine.submit_item(item("B-1", "grpB", candidate_name="온라인 창업"))
    keep = engine.candidates[0].candidateId
    drop = engine.candidates[1].candidateId
    engine.merge_candidates(keep, drop)
    dropped = next(c for c in engine.candidates if c.candidateId == drop)
    assert dropped.status == MERGED
    assert dropped.mergedIntoCandidateId == keep
    assert engine.item_classifications["B-1"].candidateId == keep


# ---- 입력 텍스트 정제 ----


# ---- 개선된 후보 재사용 로직 ----


import json as _json


class VectorBackend:
    """itemId별 임베딩 벡터와 재사용 판단을 직접 통제하는 백엔드."""

    def __init__(self, vectors, names=None, reuse_decision=None, promote=False, confident=False, convert=True):
        self.vectors = vectors
        self.names = names or {}
        self.reuse_decision = reuse_decision
        self.promote = promote
        self.confident = confident
        self.convert = convert
        self._current = None

    def classify_formal(self, item, formal_categories):
        self._current = item["testId"]
        if self.confident:  # 첫 카테고리에 확신 분류(top 0.9, 큰 gap)
            return [{"categoryId": c["id"], "score": (0.9 if i == 0 else 0.1)} for i, c in enumerate(formal_categories)]
        return [{"categoryId": c["id"], "score": 0.2} for c in formal_categories]  # 애매

    def embed(self, text):
        return l2_normalize(list(self.vectors[self._current]))

    def propose_candidate(self, item, formal_categories, top_scores):
        return {
            "needsNew": True,
            "name": self.names.get(item["testId"], item["testId"]),
            "description": "설명",
            "reason": "이유",
        }

    def review_reuse(self, item, candidate_infos):
        decision = self.reuse_decision
        if callable(decision):
            return decision(item, candidate_infos)
        return decision or {"action": "CREATE", "candidateId": None, "confidence": 0.5, "reason": "기본"}

    def review_candidate_entry(self, item, formal_category_name, candidate_infos, *, formal_confident):
        name = self.names.get(item["testId"], item["testId"])
        if not candidate_infos:  # 첫 후보는 무조건 생성
            return {"action": "CREATE", "candidateId": None, "name": name, "description": "d", "confidence": 0.8, "reason": "첫 후보"}
        d = self.reuse_decision
        dec = d(item, candidate_infos) if callable(d) else (d or {"action": "CREATE", "candidateId": None})
        return {
            "action": str(dec.get("action", "CREATE")).upper(),
            "candidateId": dec.get("candidateId"),
            "name": name, "description": "d",
            "confidence": dec.get("confidence", 0.8), "reason": dec.get("reason", ""),
        }

    def review_signal_conversion(self, item, signal_info):
        return {"convert": bool(self.convert), "name": signal_info.get("suggestedName") or item["testId"],
                "description": "d", "confidence": 0.9, "reason": "전환"}

    def review_promotion(self, candidate, linked_items):
        return {"promote": self.promote, "reason": "테스트"}


def vec_item(test_id):
    body = _json.dumps({"type": "MEMO", "title": test_id, "content": test_id, "summary": test_id}, ensure_ascii=False)
    return {"testId": test_id, "title": test_id, "inputType": "memo", "input": body}


def _engine(backend, config):
    clock = itertools.count()
    base = datetime(2026, 8, 4, 17, 0, 0, tzinfo=timezone.utc)
    return WorkspaceCategoryEngine(
        10, SEEDS, backend, config, now_fn=lambda: base.replace(microsecond=next(clock) % 1000)
    )


def test_config_nested_candidate_and_backward_compat():
    nested = ServiceConfig.from_mapping(
        {"candidate": {"center-similarity-threshold": 0.7, "item-similarity-threshold": 0.72, "ai-review-lower-bound": 0.55}}
    )
    assert nested.center_similarity_threshold == 0.7
    assert nested.item_similarity_threshold == 0.72
    assert nested.ai_review_lower_bound == 0.55
    # 중첩 블록이 없으면 기존 candidate-similarity-threshold로 하위 호환
    legacy = ServiceConfig.from_mapping({"candidate-similarity-threshold": 0.83})
    assert legacy.center_similarity_threshold == 0.83
    assert legacy.item_similarity_threshold == 0.83


def test_reuse_by_max_item_similarity_even_if_center_low():
    # A,B가 한 후보에 묶여 대표 임베딩이 희석되지만, C는 A와 동일 → maxItemSimilarity로 재사용
    backend = VectorBackend(
        vectors={"A": [1, 0, 0], "B": [0, 1, 0], "C": [1, 0, 0]},
        reuse_decision={"action": "REUSE", "candidateId": 1, "confidence": 0.9, "reason": "AI"},
    )
    config = ServiceConfig(
        center_similarity_threshold=0.75, item_similarity_threshold=0.78,
        ai_review_lower_bound=0.0, candidate_min_support_count=99,
    )
    engine = _engine(backend, config)
    engine.submit_item(vec_item("A"))       # 후보1 생성
    engine.submit_item(vec_item("B"))       # AI가 후보1 재사용(대표 희석)
    log_c = engine.submit_item(vec_item("C"))
    assert log_c["candidateAction"] == "REUSE_EMBEDDING"
    assert log_c["maxItemSimilarity"] >= 0.78
    assert log_c["centerSimilarity"] < 0.75
    active = [c for c in engine.candidates if c.status == PENDING]
    assert len(active) == 1
    assert active[0].supportCount == 3


def test_ai_review_reuse_when_embedding_ambiguous():
    backend = VectorBackend(
        vectors={"A": [1, 0, 0], "B": [0.7, 0.714, 0]},
        reuse_decision={"action": "REUSE", "candidateId": 1, "confidence": 0.9, "reason": "같은 주제"},
    )
    config = ServiceConfig(
        center_similarity_threshold=0.75, item_similarity_threshold=0.78,
        ai_review_lower_bound=0.6, candidate_min_support_count=99,
    )
    engine = _engine(backend, config)
    engine.submit_item(vec_item("A"))
    log_b = engine.submit_item(vec_item("B"))  # centerSim~0.7 (임베딩 미달) → AI 진입판단 REUSE
    assert log_b["candidateAction"] == "REUSE_AI"
    assert log_b["candidateEntryDecision"] == "REUSE"
    assert len([c for c in engine.candidates if c.status == PENDING]) == 1


def test_ai_review_create_makes_new_candidate():
    backend = VectorBackend(
        vectors={"A": [1, 0, 0], "B": [0.7, 0.714, 0]},
        reuse_decision={"action": "CREATE", "candidateId": None, "confidence": 0.8, "reason": "다른 주제"},
    )
    config = ServiceConfig(
        center_similarity_threshold=0.75, item_similarity_threshold=0.78,
        ai_review_lower_bound=0.6, candidate_min_support_count=99,
    )
    engine = _engine(backend, config)
    engine.submit_item(vec_item("A"))
    log_b = engine.submit_item(vec_item("B"))
    assert log_b["candidateAction"] == "CREATE"
    assert len([c for c in engine.candidates if c.status == PENDING]) == 2


def test_final_dedup_reuses_candidate_with_same_proposed_name():
    # 임베딩은 멀지만(AI 밴드 미만) 제안 이름이 기존 후보와 같으면 최종 단계에서 재사용
    backend = VectorBackend(
        vectors={"A": [1, 0, 0], "D": [0, 0, 1]},
        names={"A": "운세·예측", "D": " 운세·예측 "},
    )
    config = ServiceConfig(
        center_similarity_threshold=0.75, item_similarity_threshold=0.78,
        ai_review_lower_bound=0.6, candidate_min_support_count=99,
    )
    engine = _engine(backend, config)
    engine.submit_item(vec_item("A"))
    log_d = engine.submit_item(vec_item("D"))
    assert log_d["candidateAction"] == "REUSE_FINAL_DEDUP"
    assert len([c for c in engine.candidates if c.status == PENDING]) == 1


# ---- 생성 지연(잠정 신호) 정책 ----


def test_confident_singleton_defers_to_signal_not_candidate():
    backend = VectorBackend(vectors={"A": [1, 0, 0]}, confident=True)
    config = ServiceConfig(center_similarity_threshold=0.75, item_similarity_threshold=0.78,
                           signal_similarity_threshold=0.55, candidate_min_support_count=3)
    engine = _engine(backend, config)
    log = engine.submit_item(vec_item("A"))
    # 확신 분류 단발 데이터 → 후보가 아니라 잠정 신호로만 보류
    assert log["signalAction"] == "STORE_SIGNAL"
    assert log["candidateAction"] == "FORMAL_ONLY"
    assert engine.candidates == []
    assert len(engine.signals) == 1 and engine.signals[0].status == "WAITING"


def test_second_similar_confident_converts_signal_and_third_promotes():
    backend = VectorBackend(
        vectors={"A": [1, 0, 0], "B": [0.9, 0.436, 0], "C": [0.85, 0.527, 0]},
        confident=True, promote=True, convert=True,
    )
    config = ServiceConfig(center_similarity_threshold=0.75, item_similarity_threshold=0.78,
                           signal_similarity_threshold=0.55, candidate_min_support_count=3)
    engine = _engine(backend, config)
    engine.submit_item(vec_item("A"))            # 잠정 신호
    log_b = engine.submit_item(vec_item("B"))    # 2번째 유사 → 신호 전환, support 2
    assert log_b["signalAction"] == "CONVERTED"
    assert log_b["candidateAction"] == "CONVERT_SIGNAL"
    active = [c for c in engine.candidates if c.status in {PENDING, PROMOTED}]
    assert len(active) == 1 and active[0].supportCount == 2
    assert engine.signals[0].status == "CONVERTED"
    log_c = engine.submit_item(vec_item("C"))    # 3번째 → support 3 → 승격
    assert log_c["candidateAction"] == "REUSE_EMBEDDING"
    assert log_c["promoted"] is True


def test_signal_expires_after_ttl_without_reuse():
    backend = VectorBackend(
        vectors={"A": [1, 0, 0], "B": [0, 1, 0], "C": [0, 0, 1]}, confident=True,
    )
    config = ServiceConfig(signal_similarity_threshold=0.55, signal_ttl_items=1)
    engine = _engine(backend, config)
    engine.submit_item(vec_item("A"))  # input 1, expiresAtInput 2
    engine.submit_item(vec_item("B"))  # input 2 (서로 다른 주제) → A 아직 WAITING
    engine.submit_item(vec_item("C"))  # input 3 > 2 → A 만료
    a_signal = next(s for s in engine.signals if s.itemId == "A")
    assert a_signal.status == "EXPIRED"
    assert engine.candidates == []  # 재사용 없이 만료 → 후보 미생성


def test_build_service_text_drops_url_and_content_tokens_filter_numbers():
    url_item = {
        "testId": "URL-001",
        "title": "https://example.com/post/123",
        "inputType": "url",
        "input": '{"url":"https://example.com","summary":"별자리 운세 정보 2026"}',
    }
    text = build_service_text(url_item)
    assert "https" not in text  # 제목의 URL은 입력에서 제외
    tokens = content_tokens(text)
    assert "2026" not in tokens  # 연도(숫자) 제외
    assert "운세" in tokens


# ---- 핵심 대상(엔티티) 기반 매칭 (use_core_entity=True) ----


def entity_config(**kw):
    base = dict(
        use_core_entity=True,
        candidate_min_support_count=3,
        # 임베딩 임계값은 높게 둬서 엔티티 매칭 경로만 검증한다.
        center_similarity_threshold=0.99,
        item_similarity_threshold=0.99,
        signal_similarity_threshold=0.99,
        ai_review_lower_bound=0.99,
    )
    base.update(kw)
    return ServiceConfig(**base)


def test_build_embedding_text_excludes_body():
    from src.incremental_category_service import build_embedding_text

    it = {
        "title": "짱구 극장판",
        "summary": "짱구는 못말려 극장판 흥행 정리",
        "inputType": "url",
        "input": '{"content":"아주 긴 본문 내용 사토 카자마 등등"}',
    }
    text = build_embedding_text(it)
    assert "짱구" in text and "흥행" in text
    assert "본문" not in text and "사토" not in text  # 본문 완전 제외
    # URL 데이터라도 제목은 포함
    assert "극장판" in text


def test_normalize_entity_key_ignores_spacing_symbols():
    from src.incremental_category_service import normalize_entity_key

    assert normalize_entity_key("삼성 청년 SW·AI 아카데미") == normalize_entity_key("삼성청년swai아카데미")
    assert normalize_entity_key("SSAFY") == "ssafy"


def test_same_entity_defers_then_converts_then_promotes():
    backend = FakeBackend(groups=[])
    engine = make_engine(backend, entity_config())
    # 세부 내용이 달라도 같은 핵심 대상('짱구') 3건 → 신호 → 후보(support2) → 승격
    log1 = engine.submit_item(item("J1", "aaa", entity=entity("짱구")))
    log2 = engine.submit_item(item("J2", "bbb", entity=entity("짱구")))
    log3 = engine.submit_item(item("J3", "ccc", entity=entity("짱구")))

    assert log1["signalAction"] == "STORE_SIGNAL"  # 첫 데이터는 생성 지연
    assert log2["candidateAction"] == "CONVERT_SIGNAL"
    assert log2["matchMethod"] in {"ENTITY_EXACT", "ENTITY_ALIAS"}
    assert log2["candidateSupportCount"] == 2
    assert log3["matchMethod"] == "ENTITY_EXACT"
    assert log3["promoted"] is True
    active = [c for c in engine.candidates if c.status in {PENDING, READY_TO_PROMOTE, PROMOTED}]
    assert len(active) == 1
    assert active[0].supportCount == 3


def test_entity_alias_matches_same_target():
    backend = FakeBackend(groups=[])
    engine = make_engine(backend, entity_config())
    engine.submit_item(item("S1", entity=entity("SSAFY", etype="ORGANIZATION")))
    # 별칭(싸피)이 정규 이름(SSAFY)과 매칭되어야 한다
    log2 = engine.submit_item(
        item("S2", entity=entity("싸피", etype="ORGANIZATION", aliases=["SSAFY"]))
    )
    assert log2["candidateAction"] == "CONVERT_SIGNAL"
    assert log2["matchMethod"] in {"ENTITY_EXACT", "ENTITY_ALIAS"}


def test_different_entities_do_not_merge():
    backend = FakeBackend(groups=[])
    engine = make_engine(backend, entity_config())
    engine.submit_item(item("J1", entity=entity("짱구")))
    log2 = engine.submit_item(item("K1", entity=entity("SSAFY", etype="ORGANIZATION")))
    # 서로 다른 핵심 대상 → 전환되지 않고 각자 신호로 남는다
    assert log2["signalAction"] == "STORE_SIGNAL"
    assert log2["candidateAction"] == "FORMAL_ONLY"
    active = [c for c in engine.candidates if c.status in {PENDING, READY_TO_PROMOTE, PROMOTED}]
    assert active == []


def test_low_confidence_entity_is_not_used():
    backend = FakeBackend(groups=[])
    engine = make_engine(backend, entity_config())
    engine.submit_item(item("J1", entity=entity("짱구", conf=0.2)))
    log2 = engine.submit_item(item("J2", entity=entity("짱구", conf=0.2)))
    # confidence가 낮으면 엔티티 매칭을 신뢰하지 않아 신호로만 남는다
    assert log2["signalAction"] == "STORE_SIGNAL"
    assert log2["matchMethod"] is None


def test_same_entity_after_promotion_attaches_to_promoted_category():
    backend = FakeBackend(groups=[])
    engine = make_engine(backend, entity_config())
    # 같은 대상 3건 → 승격
    engine.submit_item(item("J1", entity=entity("짱구")))
    engine.submit_item(item("J2", entity=entity("짱구")))
    log3 = engine.submit_item(item("J3", entity=entity("짱구")))
    assert log3["promoted"] is True
    # 승격 후 같은 대상 4번째 → 승격된 카테고리에 2차 라벨로 연결(새 후보 아님)
    log4 = engine.submit_item(item("J4", entity=entity("짱구")))
    assert log4["candidateAction"] == "REUSE_PROMOTED_ENTITY"
    assert log4["matchMethod"] in {"ENTITY_EXACT", "ENTITY_ALIAS"}
    classification = engine.item_classifications["J4"]
    # 기본 카테고리 + 승격 대상 카테고리(최대 2개)
    assert len(classification.formalCategoryIds) <= 2
    promoted_id = next(c["id"] for c in engine.formal_categories if c["origin"] == "PROMOTED")
    assert promoted_id in classification.formalCategoryIds
    # 새 후보가 추가로 생기지 않는다
    active = [c for c in engine.candidates if c.status in {PENDING, READY_TO_PROMOTE}]
    assert active == []
