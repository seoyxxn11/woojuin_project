"""증분 카테고리(앵커) 엔진 — stateless 상태 전이 서비스.

백엔드가 전달한 현재 워크스페이스 상태(정식 카테고리·후보 shortlist·잠정 신호)를 입력받아
판단만 수행하고, 백엔드가 DB·Redis에 적용할 actions만 반환한다. 서버 전역·인메모리에
워크스페이스 상태를 보관하지 않는다.

매칭 우선순위: ENTITY_EXACT → ENTITY_ALIAS → EMBEDDING(백엔드 Top-K) → AI_REVIEW.
승격: ENTITY는 규칙 기반(3건+동일 앵커, AI 없이), UMBRELLA_TOPIC은 AI 검토 유지.
앵커 추출 실패/저신뢰면 앵커 권위 매칭을 쓰지 않고 AI 의미검증 경로로만 후보 전환.
"""

from __future__ import annotations

import re

from .category_models import (
    Action,
    CategoryAnchorOut,
    DecideCandidate,
    DecideFormalCategory,
    DecideInput,
    DecideItem,
    DecideOutput,
    DecideSignal,
    MatchOut,
    RawAnchor,
    RawConvertDecision,
    RawFormalScores,
    RawPromoteDecision,
    RawReuseDecision,
)
from .category_prompts import (
    anchor_extract_messages,
    formal_classify_messages,
    review_candidate_entry_messages,
    review_promotion_messages,
    review_signal_conversion_messages,
)
from .client import OpenRouterClient, OpenRouterError
from .config import Settings
from .service import InvalidModelResponse

_TOKEN = re.compile(r"[가-힣a-zA-Z0-9]+")


def normalize_anchor_key(name: str | None) -> str:
    if not name:
        return ""
    return "".join(_TOKEN.findall(str(name).lower()))


def _alias_keys(normalized: str | None, aliases: list[str]) -> set[str]:
    keys = set()
    primary = normalize_anchor_key(normalized)
    if primary:
        keys.add(primary)
    for alias in aliases or []:
        key = normalize_anchor_key(alias)
        if key:
            keys.add(key)
    return keys


class CategoryEngineService:
    def __init__(self, client: OpenRouterClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings

    # ---- public ----

    def decide(self, value: DecideInput) -> DecideOutput:
        item = value.item

        # 1. 정식 분류(항상 가장 가까운 기본 카테고리에 배치)
        #    base는 시드 카테고리에서만 고른다 — 승격 카테고리는 앵커 매칭으로 별도 연결한다.
        #    (승격 카테고리를 분류 대상에 넣으면 그게 최상위로 뽑혀 base+승격이 하나로 붕괴한다)
        seed_categories = [c for c in value.formal_categories if c.origin != "AI_PROMOTED"]
        classify_targets = seed_categories or value.formal_categories
        scores = self._classify_formal(item, classify_targets)
        base_id, ambiguous = self._select_formal(scores, classify_targets)
        actions: list[Action] = [Action(type="LINK_FORMAL_CATEGORY", category_id=base_id)]
        formal_ids: list[int] = [base_id]
        base_name = self._name_of(base_id, value.formal_categories)

        # 2. 카테고리 앵커 추출(실패/저신뢰는 OTHER로 흡수)
        anchor = self._extract_anchor(item)
        anchor_out = CategoryAnchorOut(
            name=anchor.category_anchor_name,
            normalized_name=anchor.normalized_anchor_name or anchor.category_anchor_name,
            type=anchor.category_anchor_type,
            aliases=anchor.aliases,
            specific_entities=anchor.specific_entities,
            confidence=anchor.anchor_confidence,
        )
        usable = self._usable_anchor(anchor)
        keys = _alias_keys(anchor.normalized_anchor_name, anchor.aliases)

        match = MatchOut(type="NONE")

        # 3. 앵커 권위 매칭 (임베딩보다 우선)
        if usable:
            # A. 이미 승격된 정식 대상 카테고리 재사용
            pf, method = self._match_promoted_formal(keys, anchor, value.formal_categories)
            if pf is not None:
                if pf.category_id != base_id:
                    actions.append(
                        Action(
                            type="LINK_FORMAL_CATEGORY",
                            category_id=pf.category_id,
                            reason="이미 승격된 동일 앵커 카테고리 재사용",
                        )
                    )
                    formal_ids.append(pf.category_id)
                match = MatchOut(type="PROMOTED_FORMAL", target_id=pf.category_id, method=method)
                return self._output(value, formal_ids, ambiguous, anchor_out, match, actions)

            # B. 후보 shortlist 앵커 매칭 → 연결
            cand, method = self._match_candidate_anchor(keys, anchor, value.candidate_shortlist)
            if cand is not None:
                support_after = cand.support_count + 1
                actions.append(
                    Action(
                        type="LINK_CANDIDATE",
                        candidate_id=cand.candidate_id,
                        support_count_after=support_after,
                        reason=f"동일 앵커 후보 연결({method})",
                    )
                )
                match = MatchOut(type="CANDIDATE", target_id=cand.candidate_id, method=method)
                self._maybe_promote_action(cand, support_after, anchor, item, actions)
                return self._output(value, formal_ids, ambiguous, anchor_out, match, actions)

            # C. 잠정 신호 앵커 매칭 → 후보 생성(2번째 데이터)
            sig = value.provisional_signal
            if sig is not None:
                sig_method = self._signal_anchor_method(keys, anchor, sig)
                if sig_method is not None:
                    actions.append(self._create_candidate_action(anchor, sig, item, keys))
                    match = MatchOut(type="SIGNAL", target_id=sig.signal_id, method=sig_method)
                    return self._output(value, formal_ids, ambiguous, anchor_out, match, actions)

        # 4. 앵커 무매칭/저신뢰 → AI 의미검증 경로(임베딩만으로 전환 금지)
        if value.candidate_shortlist:
            reuse = self._review_candidate_entry(item, base_name, value.candidate_shortlist)
            if reuse.action == "REUSE" and reuse.candidate_id is not None:
                cand = next(
                    (c for c in value.candidate_shortlist if c.candidate_id == reuse.candidate_id),
                    None,
                )
                if cand is not None:
                    support_after = cand.support_count + 1
                    actions.append(
                        Action(
                            type="LINK_CANDIDATE",
                            candidate_id=cand.candidate_id,
                            support_count_after=support_after,
                            reason="AI 의미검증 후 후보 재사용",
                        )
                    )
                    match = MatchOut(type="CANDIDATE", target_id=cand.candidate_id, method="AI_REVIEW")
                    self._maybe_promote_action(cand, support_after, anchor, item, actions)
                    return self._output(value, formal_ids, ambiguous, anchor_out, match, actions)

        sig = value.provisional_signal
        if sig is not None:
            conv = self._review_signal_conversion(item, sig)
            if conv.convert:
                actions.append(self._create_candidate_action(anchor, sig, item, keys))
                match = MatchOut(type="SIGNAL", target_id=sig.signal_id, method="AI_REVIEW")
                return self._output(value, formal_ids, ambiguous, anchor_out, match, actions)

        # 5. 매칭 없음 → 잠정 신호 보류(생성 지연)
        actions.append(
            Action(
                type="STORE_SIGNAL",
                suggested_name=self._signal_name(anchor, item),
                anchor_type=anchor.category_anchor_type,
                normalized_anchor_name=anchor.normalized_anchor_name or None,
                aliases=anchor.aliases or None,
                link_item_ids=[item.item_id],
                reason="매칭 없음 단발 데이터 → 잠정 신호 보류",
            )
        )
        return self._output(value, formal_ids, ambiguous, anchor_out, match, actions)

    # ---- 매칭 헬퍼 ----

    def _usable_anchor(self, anchor: RawAnchor) -> bool:
        if anchor.category_anchor_type == "OTHER":
            return False
        if not normalize_anchor_key(anchor.normalized_anchor_name or anchor.category_anchor_name):
            return False
        return anchor.anchor_confidence >= self.settings.anchor_min_confidence

    def _match_promoted_formal(self, keys, anchor, formals):
        primary = normalize_anchor_key(anchor.normalized_anchor_name or anchor.category_anchor_name)
        promoted = [c for c in formals if c.origin == "AI_PROMOTED"]
        for c in promoted:
            if normalize_anchor_key(c.normalized_anchor_name) == primary and primary:
                return c, "ENTITY_EXACT"
        for c in promoted:
            if keys & _alias_keys(c.normalized_anchor_name, c.aliases):
                return c, "ENTITY_ALIAS"
        return None, None

    def _match_candidate_anchor(self, keys, anchor, candidates):
        primary = normalize_anchor_key(anchor.normalized_anchor_name or anchor.category_anchor_name)
        for c in candidates:
            if normalize_anchor_key(c.normalized_anchor_name) == primary and primary:
                return c, "ENTITY_EXACT"
        for c in candidates:
            if keys & _alias_keys(c.normalized_anchor_name, c.aliases):
                return c, "ENTITY_ALIAS"
        return None, None

    def _signal_anchor_method(self, keys, anchor, sig: DecideSignal):
        primary = normalize_anchor_key(anchor.normalized_anchor_name or anchor.category_anchor_name)
        if primary and normalize_anchor_key(sig.normalized_anchor_name) == primary:
            return "ENTITY_EXACT"
        if keys & _alias_keys(sig.normalized_anchor_name, sig.aliases):
            return "ENTITY_ALIAS"
        return None

    def _create_candidate_action(self, anchor, sig: DecideSignal, item: DecideItem, keys) -> Action:
        link_items = [i for i in (sig.first_item_id, item.item_id) if i]
        name = anchor.category_anchor_name or anchor.normalized_anchor_name or (item.title or "세부주제")
        return Action(
            type="CREATE_CANDIDATE",
            suggested_name=str(name)[:100],
            anchor_type=anchor.category_anchor_type if anchor.category_anchor_type != "OTHER" else None,
            normalized_anchor_name=anchor.normalized_anchor_name or None,
            aliases=sorted(keys) or None,
            link_item_ids=link_items or None,
            support_count_after=2,
            reason="동일 대상 2번째 데이터 → 후보 생성(supportCount 2)",
        )

    def _maybe_promote_action(self, cand: DecideCandidate, support_after, anchor, item, actions):
        if support_after < self.settings.category_min_support_count:
            return
        atype = cand.anchor_type or anchor.category_anchor_type
        if atype == "ENTITY":
            actions.append(
                Action(
                    type="PROMOTE_CANDIDATE",
                    candidate_id=cand.candidate_id,
                    category_name=cand.suggested_name,
                    anchor_type="ENTITY",
                    reason="ENTITY 규칙 기반 승격(동일 앵커 3건+confidence)",
                )
            )
            return
        # UMBRELLA_TOPIC / 기타 → AI 승격 검토(과잉 일반화 방지)
        samples = [r.title for r in cand.representative_items if r.title]
        if item.title:
            samples.append(item.title)
        promote = self._review_promotion(cand.suggested_name, samples)
        if promote.promote:
            actions.append(
                Action(
                    type="PROMOTE_CANDIDATE",
                    candidate_id=cand.candidate_id,
                    category_name=cand.suggested_name,
                    anchor_type=atype if atype != "OTHER" else None,
                    reason=f"AI 승격 검토 통과: {promote.reason}"[:300],
                )
            )

    def _signal_name(self, anchor: RawAnchor, item: DecideItem) -> str:
        if anchor.category_anchor_name and anchor.category_anchor_type != "OTHER":
            return anchor.category_anchor_name[:100]
        return (item.title or "세부주제")[:100]

    # ---- 정식 분류 ----

    def _select_formal(self, scores: dict[int, float], formals):
        ranked = sorted(formals, key=lambda c: scores.get(c.category_id, 0.0), reverse=True)
        top = ranked[0]
        top_score = scores.get(top.category_id, 0.0)
        second = scores.get(ranked[1].category_id, 0.0) if len(ranked) > 1 else 0.0
        ambiguous = (
            top_score < self.settings.category_score_threshold
            or (top_score - second) < self.settings.category_score_gap_threshold
        )
        return top.category_id, ambiguous

    @staticmethod
    def _name_of(category_id: int, formals) -> str:
        return next((c.name for c in formals if c.category_id == category_id), "")

    # ---- AI 호출 ----

    def _classify_formal(self, item: DecideItem, formals) -> dict[int, float]:
        valid = {c.category_id for c in formals}
        try:
            raw = self.client.chat_json(
                messages=formal_classify_messages(item, formals),
                schema=RawFormalScores.model_json_schema(by_alias=True),
                schema_name="formal_classification",
            )
            parsed = RawFormalScores.model_validate(raw)
            scores = {s.category_id: s.score for s in parsed.scores if s.category_id in valid}
        except (OpenRouterError, InvalidModelResponse, ValueError):
            scores = {}
        for cid in valid:
            scores.setdefault(cid, 0.0)
        return scores

    def _extract_anchor(self, item: DecideItem) -> RawAnchor:
        try:
            raw = self.client.chat_json(
                messages=anchor_extract_messages(item),
                schema=RawAnchor.model_json_schema(by_alias=True),
                schema_name="category_anchor",
            )
            return RawAnchor.model_validate(raw)
        except (OpenRouterError, InvalidModelResponse, ValueError):
            return RawAnchor(
                category_anchor_name="",
                category_anchor_type="OTHER",
                normalized_anchor_name="",
                specific_entities=[],
                aliases=[],
                anchor_confidence=0.0,
                anchor_evidence="추출 실패",
            )

    def _review_candidate_entry(self, item, base_name, candidates) -> RawReuseDecision:
        try:
            raw = self.client.chat_json(
                messages=review_candidate_entry_messages(item, base_name, candidates),
                schema=RawReuseDecision.model_json_schema(by_alias=True),
                schema_name="candidate_entry_review",
            )
            return RawReuseDecision.model_validate(raw)
        except (OpenRouterError, InvalidModelResponse, ValueError):
            return RawReuseDecision(action="SKIP", reason="AI 응답 실패")

    def _review_signal_conversion(self, item, sig) -> RawConvertDecision:
        try:
            raw = self.client.chat_json(
                messages=review_signal_conversion_messages(item, sig),
                schema=RawConvertDecision.model_json_schema(by_alias=True),
                schema_name="signal_conversion_review",
            )
            return RawConvertDecision.model_validate(raw)
        except (OpenRouterError, InvalidModelResponse, ValueError):
            return RawConvertDecision(convert=False, reason="AI 응답 실패")

    def _review_promotion(self, name, samples) -> RawPromoteDecision:
        try:
            raw = self.client.chat_json(
                messages=review_promotion_messages(name, samples),
                schema=RawPromoteDecision.model_json_schema(by_alias=True),
                schema_name="promotion_review",
            )
            return RawPromoteDecision.model_validate(raw)
        except (OpenRouterError, InvalidModelResponse, ValueError):
            return RawPromoteDecision(promote=False, reason="AI 응답 실패")

    # ---- 출력 ----

    @staticmethod
    def _output(value, formal_ids, ambiguous, anchor_out, match, actions) -> DecideOutput:
        return DecideOutput(
            workspace_id=value.workspace_id,
            item_id=value.item.item_id,
            formal_category_ids=formal_ids,
            ambiguous=ambiguous,
            category_anchor=anchor_out,
            match=match,
            actions=actions,
        )
