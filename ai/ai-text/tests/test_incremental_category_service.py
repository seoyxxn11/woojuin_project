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


def item(test_id, group="", *, candidate_name=None, title=None):
    text = f"{test_id} {group}"
    return {
        "testId": test_id,
        "title": title if title is not None else text,
        "inputType": "memo",
        "input": text,
        "candidateName": candidate_name,
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
