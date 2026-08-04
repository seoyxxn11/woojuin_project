"""실제 서비스처럼 데이터를 한 건씩 받아 분류하는 증분 카테고리 엔진.

핵심 개념
- 정식(FORMAL) 카테고리: 사용자에게 노출되는 카테고리. 기본 5개로 시작하고
  임시 후보가 승격되면 늘어난다. 워크스페이스당 최대 10개.
- 임시(TEMPORARY) 후보: 사용자에게 노출하지 않는 내부 후보. 정식 분류가 애매한
  데이터를 모아 반복 주제를 확인하고, 조건을 만족하면 정식으로 승격한다.

데이터 한 건 처리 흐름은 ``WorkspaceCategoryEngine.submit_item`` 참고.

정식 분류 점수와 후보 이름/설명 생성, 승격 검토는 백엔드(``ServiceBackend``)에
위임한다. 오프라인 결정론 백엔드(``DeterministicBackend``)는 API 없이도 흐름을
재현하고, 실제 실행에서는 임베딩·AI 모델을 쓰는 백엔드로 교체한다.
"""

from __future__ import annotations

import hashlib
import math
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from .dynamic_category_experiment import (
    category_key,
    generated_category_id,
    name_tokens,
    normalize_category_name,
)

# ---- 후보 상태 ----
PENDING = "PENDING"
READY_TO_PROMOTE = "READY_TO_PROMOTE"
PROMOTED = "PROMOTED"
MERGED = "MERGED"
EXPIRED = "EXPIRED"
REJECTED = "REJECTED"
CANDIDATE_STATUSES = (PENDING, READY_TO_PROMOTE, PROMOTED, MERGED, EXPIRED, REJECTED)

# ---- 데이터 분류 상태 ----
FORMAL_ONLY = "FORMAL_ONLY"
MULTI_LABEL_FORMAL = "MULTI_LABEL_FORMAL"
CANDIDATE_LINKED = "CANDIDATE_LINKED"

# ---- 카테고리 출처 ----
SEED = "SEED"
PROMOTED_ORIGIN = "PROMOTED"


@dataclass(frozen=True)
class ServiceConfig:
    """유사도 임계값과 승격 조건. 코드가 아닌 설정에서 주입한다."""

    max_count: int = 10
    max_ai_generated_count: int = 5
    formal_confidence_threshold: float = 0.65
    formal_score_gap_threshold: float = 0.10
    candidate_similarity_threshold: float = 0.80
    candidate_min_support_count: int = 3
    candidate_consistency_threshold: float = 0.75
    service_max_categories: int = 2
    # 개선된 후보 재사용 판단용 임계값
    center_similarity_threshold: float = 0.75
    item_similarity_threshold: float = 0.78
    ai_review_lower_bound: float = 0.60

    @classmethod
    def from_mapping(cls, mapping: dict[str, Any] | None) -> "ServiceConfig":
        data = dict(mapping or {})

        def pick(*keys: str, default: Any) -> Any:
            for key in keys:
                if key in data and data[key] is not None:
                    return data[key]
            return default

        legacy_similarity = float(
            pick("candidate-similarity-threshold", "candidate_similarity_threshold", default=0.80)
        )
        # 중첩 category.candidate.* 블록이 있으면 우선 사용, 없으면 기존 값으로 하위 호환.
        candidate_block = data.get("candidate")
        if not isinstance(candidate_block, dict):
            candidate_block = {}

        def pick_candidate(*keys: str, default: Any) -> Any:
            for key in keys:
                if key in candidate_block and candidate_block[key] is not None:
                    return candidate_block[key]
            return default

        return cls(
            max_count=int(pick("max-count", "max_count", default=10)),
            max_ai_generated_count=int(
                pick("max-ai-generated-count", "max_ai_generated_count", default=5)
            ),
            formal_confidence_threshold=float(
                pick("formal-confidence-threshold", "formal_confidence_threshold", default=0.65)
            ),
            formal_score_gap_threshold=float(
                pick("formal-score-gap-threshold", "formal_score_gap_threshold", default=0.10)
            ),
            candidate_similarity_threshold=legacy_similarity,
            candidate_min_support_count=int(
                pick("candidate-min-support-count", "candidate_min_support_count", default=3)
            ),
            candidate_consistency_threshold=float(
                pick(
                    "candidate-consistency-threshold",
                    "candidate_consistency_threshold",
                    default=0.75,
                )
            ),
            service_max_categories=int(
                pick("service-max-categories", "service_max_categories", default=2)
            ),
            center_similarity_threshold=float(
                pick_candidate(
                    "center-similarity-threshold",
                    "center_similarity_threshold",
                    default=legacy_similarity,
                )
            ),
            item_similarity_threshold=float(
                pick_candidate(
                    "item-similarity-threshold",
                    "item_similarity_threshold",
                    default=legacy_similarity,
                )
            ),
            ai_review_lower_bound=float(
                pick_candidate(
                    "ai-review-lower-bound", "ai_review_lower_bound", default=0.60
                )
            ),
        )


@dataclass
class TemporaryCandidate:
    candidateId: int
    workspaceId: int
    suggestedName: str
    description: str
    status: str
    supportCount: int
    representativeEmbedding: list[float]
    createdAt: str
    updatedAt: str
    createdAtItemId: str
    linkedItemIds: list[str] = field(default_factory=list)
    sumEmbedding: list[float] = field(default_factory=list)
    mergedIntoCandidateId: int | None = None
    promotedFormalCategoryId: str | None = None
    lastReviewReason: str | None = None

    def public_dict(self) -> dict[str, Any]:
        """대표 임베딩 원본 대신 차원만 노출한 직렬화."""
        return {
            "candidateId": self.candidateId,
            "workspaceId": self.workspaceId,
            "suggestedName": self.suggestedName,
            "description": self.description,
            "status": self.status,
            "supportCount": self.supportCount,
            "representativeEmbeddingDim": len(self.representativeEmbedding),
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
            "createdAtItemId": self.createdAtItemId,
            "linkedItemIds": list(self.linkedItemIds),
            "mergedIntoCandidateId": self.mergedIntoCandidateId,
            "promotedFormalCategoryId": self.promotedFormalCategoryId,
            "lastReviewReason": self.lastReviewReason,
        }


@dataclass
class CandidateItemLink:
    candidateId: int
    itemId: str
    similarity: float


@dataclass
class ItemClassification:
    itemId: str
    formalCategoryId: str
    formalCategoryIds: list[str]
    candidateId: int | None
    classificationStatus: str


# ---- 백엔드 프로토콜 ----


class ServiceBackend(Protocol):
    def embed(self, text: str) -> list[float]:
        ...

    def classify_formal(
        self, item: dict[str, Any], formal_categories: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """[{"categoryId": str, "score": float(0~1)}] 형태로 반환한다."""
        ...

    def propose_candidate(
        self,
        item: dict[str, Any],
        formal_categories: list[dict[str, Any]],
        top_scores: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """{"needsNew": bool, "name": str, "description": str, "reason": str}"""
        ...

    def review_promotion(
        self, candidate: TemporaryCandidate, linked_items: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """{"promote": bool, "reason": str}"""
        ...

    def review_reuse(
        self, item: dict[str, Any], candidate_infos: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """(구) 임베딩 애매 시 기존 후보 재사용 여부 판단. review_candidate_entry로 대체됨."""
        ...

    def review_candidate_entry(
        self,
        item: dict[str, Any],
        formal_category_name: str,
        candidate_infos: list[dict[str, Any]],
        *,
        formal_confident: bool,
    ) -> dict[str, Any]:
        """정식 분류가 확신이어도, 반복 가능한 더 구체적인 세부 주제인지 판단한다.

        candidate_infos: [{candidateId, name, description, supportCount,
        representativeItems:[{title, summary}], centerSimilarity, maxItemSimilarity}]
        반환: {"action": "REUSE"|"CREATE"|"SKIP", "candidateId": int|None,
               "name": str, "description": str, "confidence": float, "reason": str}
        - REUSE: 기존 세부주제 후보와 같음 → 그 후보에 병행 연결
        - CREATE: 정식 카테고리보다 구체적이고 반복될 세부 주제 → 신규 후보
        - SKIP: 그냥 정식 카테고리의 일반적인 데이터 → 후보 만들지 않음
        """
        ...


# ---- 임베딩 유틸 ----

_TOKEN_PATTERN = re.compile(r"[가-힣a-zA-Z0-9]+")
_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
# URL·웹 공통 토큰과 의미 없는 불용어. 이름/임베딩 품질을 떨어뜨려 제외한다.
STOP_TOKENS = {
    "https", "http", "www", "com", "co", "kr", "net", "org", "html", "htm", "php",
    "index", "page", "id", "the", "of", "and", "to", "in", "for", "on", "at",
    "정보", "사이트", "링크", "페이지", "관련", "이번", "오늘", "무료", "확인",
}


def _strip_urls(text: str) -> str:
    return _URL_PATTERN.sub(" ", str(text))


def service_tokens(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_PATTERN.findall(_strip_urls(text))]


def content_tokens(text: str) -> list[str]:
    """이름 생성용: 불용어·웹 토큰·한 글자·순수 숫자(연도 등)를 제외한 토큰."""
    return [
        token
        for token in service_tokens(text)
        if len(token) >= 2 and token not in STOP_TOKENS and not token.isdigit()
    ]


def feature_hash_embedding(text: str, dim: int = 512) -> list[float]:
    """토큰 백오브워즈를 해시해 결정론적 임베딩을 만든다(코사인 0~1)."""
    vector = [0.0] * dim
    for token in service_tokens(text):
        digest = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        vector[digest % dim] += 1.0
    return l2_normalize(vector)


def l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return list(vector)
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    return max(-1.0, min(1.0, dot))


def mean_vector(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    dim = len(vectors[0])
    total = [0.0] * dim
    for vector in vectors:
        for index in range(dim):
            total[index] += vector[index]
    return [value / len(vectors) for value in total]


def build_service_text(item: dict[str, Any]) -> str:
    """제목 + 요약 + 키워드 + 정제된 본문 일부를 임베딩 입력으로 합친다.

    URL 데이터는 title에 원문 URL이 들어갈 수 있어, URL 자체는 입력에서 제거한다.
    """
    parts: list[str] = []
    title = str(item.get("title", "")).strip()
    if title and str(item.get("inputType", "")).lower() != "url" and not _URL_PATTERN.match(title):
        parts.append(title)
    summary = str(item.get("summary") or _summary_from_input(item)).strip()
    if summary:
        parts.append(summary)
    keywords = item.get("keywords")
    if isinstance(keywords, (list, tuple)) and keywords:
        parts.append(" ".join(str(word) for word in keywords))
    body = _body_excerpt(item)
    if body:
        parts.append(body)
    return "\n".join(parts) if parts else title or str(item.get("testId", ""))


def _summary_from_input(item: dict[str, Any]) -> str:
    import json

    raw = str(item.get("input", ""))
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return raw[:400]
    if not isinstance(value, dict):
        return raw[:400]
    return str(
        value.get("summary")
        or value.get("preview", {}).get("description")
        or value.get("content")
        or ""
    ).strip()


def _body_excerpt(item: dict[str, Any], limit: int = 400) -> str:
    import json

    raw = str(item.get("input", ""))
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return raw[:limit]
    if isinstance(value, dict):
        body = str(value.get("content") or value.get("summary") or "").strip()
        return body[:limit]
    return raw[:limit]


# ---- 결정론 백엔드 (오프라인) ----


# 오프라인 데모용 개념 확장 맵. 실제 임베딩이 잡아내는 의미 유사성을 결정론
# 백엔드에서 흉내 내기 위해, 서로 다른 표현이지만 같은 주제인 토큰을 공통 개념
# 토큰으로 확장한다. 실제 실행에서는 의미 임베딩을 쓰는 백엔드를 사용하므로 이
# 맵이 필요 없다. 여기 없는 주제는 순수 토큰 겹침으로만 비교된다.
CONCEPT_TOKEN_MAP: dict[str, str] = {}
for _concept, _surface in {
    "운세": ["운세", "별자리", "사주", "타로", "궁합", "점성", "사주풀이", "타로카드", "띠별", "역술"],
    "창업": ["창업", "사업", "부업", "스타트업", "자영업", "장사", "아이템"],
    "심리": ["심리", "성격", "mbti", "자기이해", "성격유형", "심리테스트", "에니어그램"],
    "재테크": ["재테크", "주식", "투자", "적금", "예금", "etf", "펀드", "배당"],
    "레시피": ["레시피", "요리", "조리", "볶음밥", "찌개", "식재료", "메뉴"],
}.items():
    for _token in _surface:
        CONCEPT_TOKEN_MAP[_token] = _concept


@dataclass
class DeterministicBackend:
    """API 없이 흐름을 재현하는 백엔드.

    임베딩은 토큰 해시(feature hashing), 정식 분류 점수는 데이터와 카테고리 시드
    임베딩의 코사인 유사도, 후보 승격 검토는 후보 내부 일관성으로 판정한다.
    ``concept_map``으로 표현이 다른 동일 주제 토큰을 공통 개념으로 확장한다.
    """

    dim: int = 512
    consistency_threshold: float = 0.30
    concept_map: dict[str, str] = field(default_factory=lambda: dict(CONCEPT_TOKEN_MAP))
    _seed_cache: dict[str, list[float]] = field(default_factory=dict)

    def _expand(self, text: str) -> str:
        tokens = service_tokens(text)
        expanded = list(tokens)
        for token in tokens:
            concept = self.concept_map.get(token)
            if concept:
                # 개념 토큰을 강조해 같은 주제가 공통 차원에서 강하게 겹치게 한다.
                expanded.extend([f"개념_{concept}"] * 3)
        return " ".join(expanded)

    def embed(self, text: str) -> list[float]:
        return feature_hash_embedding(self._expand(text), self.dim)

    def _category_embedding(self, category: dict[str, Any]) -> list[float]:
        key = str(category.get("id", ""))
        cached = self._seed_cache.get(key)
        if cached is not None:
            return cached
        parts = [str(category.get("name", "")), str(category.get("description", ""))]
        parts.extend(str(example) for example in category.get("examples", []) or [])
        # 카테고리도 개념 확장해 데이터와 같은 개념 차원에서 비교되게 한다.
        vector = feature_hash_embedding(self._expand(" ".join(parts)), self.dim)
        self._seed_cache[key] = vector
        return vector

    def classify_formal(
        self, item: dict[str, Any], formal_categories: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        item_vector = self.embed(build_service_text(item))
        scores = []
        for category in formal_categories:
            similarity = cosine_similarity(item_vector, self._category_embedding(category))
            scores.append({"categoryId": str(category["id"]), "score": max(0.0, similarity)})
        return scores

    def propose_candidate(
        self,
        item: dict[str, Any],
        formal_categories: list[dict[str, Any]],
        top_scores: list[dict[str, Any]],
    ) -> dict[str, Any]:
        text = build_service_text(item)
        # 개념 맵에 걸리는 토큰이 있으면 그 개념을 대표 이름으로 우선 사용한다.
        concept = next(
            (self.concept_map[token] for token in service_tokens(text) if token in self.concept_map),
            None,
        )
        seen: list[str] = []
        for token in content_tokens(text):
            if token not in seen:
                seen.append(token)
            if len(seen) >= 2:
                break
        if concept:
            name = concept
        else:
            name = "·".join(seen) if seen else f"후보-{item.get('testId', '')}"
        return {
            "needsNew": True,
            "name": name[:12],
            "description": f"{name} 관련 반복 주제 후보",
            "reason": "정식 카테고리로 표현하기 어려운 반복 주제",
        }

    def review_promotion(
        self, candidate: TemporaryCandidate, linked_items: list[dict[str, Any]]
    ) -> dict[str, Any]:
        vectors = [self.embed(build_service_text(entry)) for entry in linked_items]
        if len(vectors) < 2:
            return {"promote": False, "reason": "연결 데이터 부족"}
        representative = mean_vector(vectors)
        similarities = [cosine_similarity(vector, representative) for vector in vectors]
        consistency = sum(similarities) / len(similarities)
        if consistency >= self.consistency_threshold:
            return {
                "promote": True,
                "reason": f"후보 내부 일관성 충족 (평균 {consistency:.2f})",
            }
        return {
            "promote": False,
            "reason": f"공통 주제가 약함 (평균 일관성 {consistency:.2f})",
        }

    def review_reuse(
        self, item: dict[str, Any], candidate_infos: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """임베딩만으로 애매한 경우: 가장 유사한 후보의 유사도가 충분하면 재사용."""
        if not candidate_infos:
            return {"action": "CREATE", "candidateId": None, "confidence": 0.5, "reason": "후보 없음"}
        best = max(
            candidate_infos,
            key=lambda info: max(info["centerSimilarity"], info["maxItemSimilarity"]),
        )
        score = max(best["centerSimilarity"], best["maxItemSimilarity"])
        # 결정론 백엔드는 하한(0.6 근처) 이상이면 같은 주제로 간주해 재사용한다.
        if score >= 0.6:
            return {
                "action": "REUSE",
                "candidateId": best["candidateId"],
                "confidence": round(score, 3),
                "reason": f"기존 후보 '{best['name']}'와 의미 유사(유사도 {score:.2f})",
            }
        return {
            "action": "CREATE",
            "candidateId": None,
            "confidence": round(1 - score, 3),
            "reason": "기존 후보와 구분되는 새 주제",
        }

    def review_candidate_entry(
        self, item, formal_category_name, candidate_infos, *, formal_confident
    ) -> dict[str, Any]:
        # 유사한 기존 후보가 있으면 재사용
        if candidate_infos:
            best = max(
                candidate_infos,
                key=lambda info: max(info["centerSimilarity"], info["maxItemSimilarity"]),
            )
            score = max(best["centerSimilarity"], best["maxItemSimilarity"])
            if score >= 0.6:
                return {
                    "action": "REUSE",
                    "candidateId": best["candidateId"],
                    "name": "",
                    "description": "",
                    "confidence": round(score, 3),
                    "reason": f"기존 세부주제 '{best['name']}'와 유사(유사도 {score:.2f})",
                }
        # 개념 맵에 걸리는 뚜렷한 세부 주제만 신규 생성, 그 외는 일반 데이터로 SKIP
        text = build_service_text(item)
        concept = next(
            (self.concept_map[t] for t in service_tokens(text) if t in self.concept_map), None
        )
        if concept:
            return {
                "action": "CREATE",
                "candidateId": None,
                "name": concept,
                "description": f"{concept} 관련 반복 세부 주제",
                "confidence": 0.7,
                "reason": f"'{formal_category_name}'보다 구체적인 반복 주제({concept})",
            }
        return {
            "action": "SKIP",
            "candidateId": None,
            "name": "",
            "description": "",
            "confidence": 0.6,
            "reason": f"'{formal_category_name}'의 일반적인 데이터",
        }


def _default_clock() -> datetime:
    return datetime.now(timezone.utc).astimezone()


class WorkspaceCategoryEngine:
    """워크스페이스 하나의 정식 카테고리와 임시 후보 상태를 관리한다."""

    def __init__(
        self,
        workspace_id: int,
        seed_categories: list[dict[str, Any]],
        backend: ServiceBackend,
        config: ServiceConfig | None = None,
        *,
        now_fn: Callable[[], datetime] = _default_clock,
        candidate_merge_threshold: float | None = None,
    ) -> None:
        self.workspace_id = workspace_id
        self.backend = backend
        self.config = config or ServiceConfig()
        self._now = now_fn
        # 병합 임계값 기본값은 후보 매칭 임계값보다 조금 높게 잡는다.
        self.merge_threshold = (
            candidate_merge_threshold
            if candidate_merge_threshold is not None
            else min(0.92, self.config.candidate_similarity_threshold + 0.05)
        )
        self._lock = threading.RLock()
        self.formal_categories: list[dict[str, Any]] = []
        for definition in seed_categories:
            self.formal_categories.append(
                {
                    "id": str(definition["id"]),
                    "name": normalize_category_name(definition["name"]),
                    "description": str(definition.get("description", "")),
                    "examples": list(definition.get("examples", []) or []),
                    "origin": SEED,
                    "createdAtItemId": None,
                    "itemIds": [],
                }
            )
        self.candidates: list[TemporaryCandidate] = []
        self.links: list[CandidateItemLink] = []
        self.item_classifications: dict[str, ItemClassification] = {}
        self.history: list[dict[str, Any]] = []
        self._items: dict[str, dict[str, Any]] = {}
        self._item_embeddings: dict[str, list[float]] = {}  # maxItemSimilarity 계산용
        self._next_candidate_id = 1
        self.reclassified_item_ids: set[str] = set()

    # ---- 조회 헬퍼 ----

    def _formal_by_id(self, category_id: str) -> dict[str, Any] | None:
        return next((c for c in self.formal_categories if c["id"] == category_id), None)

    def _active_candidates(self) -> list[TemporaryCandidate]:
        return [c for c in self.candidates if c.status in {PENDING, READY_TO_PROMOTE}]

    def _candidate_by_id(self, candidate_id: int) -> TemporaryCandidate | None:
        return next((c for c in self.candidates if c.candidateId == candidate_id), None)

    def promoted_count(self) -> int:
        return sum(1 for c in self.formal_categories if c["origin"] == PROMOTED_ORIGIN)

    # ---- 핵심: 데이터 한 건 처리 ----

    def submit_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """데이터 한 건을 처리하고 처리 결과 로그를 반환한다.

        원본 저장과 정식 분류는 항상 성공하며, 후보 처리 실패는 격리한다.
        """
        item_id = str(item["testId"])
        with self._lock:
            if item_id in self.item_classifications:
                return self._log_for(item_id, note="ALREADY_PROCESSED")
            self._items[item_id] = item

            # 1~2. 정식 카테고리 분류 (AI 점수)
            scores = self.backend.classify_formal(item, self._formal_snapshot())
            ordered = sorted(scores, key=lambda entry: float(entry["score"]), reverse=True)
            top_score = float(ordered[0]["score"]) if ordered else 0.0
            second_score = float(ordered[1]["score"]) if len(ordered) > 1 else 0.0
            gap = top_score - second_score
            nearest_id = str(ordered[0]["categoryId"]) if ordered else self.formal_categories[0]["id"]

            above = [
                str(entry["categoryId"])
                for entry in ordered
                if float(entry["score"]) >= self.config.formal_confidence_threshold
            ]
            formal_ids = above[: self.config.service_max_categories] or [nearest_id]
            ambiguous = (
                top_score < self.config.formal_confidence_threshold
                or gap < self.config.formal_score_gap_threshold
            )

            log: dict[str, Any] = {
                "itemId": item_id,
                "title": item.get("title", ""),
                "inputType": item.get("inputType", ""),
                "formalTopScore": round(top_score, 4),
                "formalScoreGap": round(gap, 4),
                "ambiguous": ambiguous,
                "selectedFormalCategoryId": nearest_id,
                "selectedFormalCategoryIds": formal_ids,
                "formalConfident": not ambiguous,
                "matchedExistingCandidate": False,
                "linkedCandidateId": None,
                "candidateName": None,
                "newCandidateCreated": False,
                "candidateSupportCount": None,
                "candidateAction": "FORMAL_ONLY",
                "centerSimilarity": None,
                "maxItemSimilarity": None,
                "candidateEntryDecision": None,
                "candidateEntryReason": None,
                "promoted": False,
                "reclassified": False,
                "candidateError": None,
            }

            classification = ItemClassification(
                itemId=item_id,
                formalCategoryId=nearest_id,
                formalCategoryIds=formal_ids,
                candidateId=None,
                classificationStatus=(
                    MULTI_LABEL_FORMAL if len(formal_ids) > 1 else FORMAL_ONLY
                ),
            )
            self.item_classifications[item_id] = classification
            formal = self._formal_by_id(nearest_id)
            if formal is not None:
                formal["itemIds"].append(item_id)

            # 3~8. 후보 처리: 확신 분류 여부와 무관하게 세부 주제 진입을 평가한다.
            # (데이터는 이미 가장 가까운 정식 카테고리에 배치됐고, 후보 연결은 병행 표시)
            try:
                self._handle_candidate(item, item_id, ordered, classification, log, ambiguous)
            except Exception as exc:  # noqa: BLE001 - 후보 처리 실패 격리
                log["candidateError"] = str(exc)

            log["formalCategoryCount"] = len(self.formal_categories)
            log["candidateCount"] = len(self._active_candidates())
            log["classificationStatus"] = classification.classificationStatus
            self.history.append(log)
            return log

    def _similarity_infos(
        self, embedding: list[float]
    ) -> list[tuple[TemporaryCandidate, float, float]]:
        """활성 후보별 (centerSimilarity, maxItemSimilarity)를 계산한다."""
        infos: list[tuple[TemporaryCandidate, float, float]] = []
        for candidate in self._active_candidates():
            center = cosine_similarity(embedding, candidate.representativeEmbedding)
            item_sims = [
                cosine_similarity(embedding, self._item_embeddings[linked])
                for linked in candidate.linkedItemIds
                if linked in self._item_embeddings
            ]
            max_item = max(item_sims) if item_sims else center
            infos.append((candidate, center, max_item))
        return infos

    def _ai_candidate_info(
        self, sim: tuple[TemporaryCandidate, float, float]
    ) -> dict[str, Any]:
        candidate, center, max_item = sim
        reps = []
        for linked in candidate.linkedItemIds[:3]:
            entry = self._items.get(linked, {})
            reps.append(
                {
                    "title": str(entry.get("title", "")),
                    "summary": str(entry.get("summary") or _summary_from_input(entry))[:200],
                }
            )
        return {
            "candidateId": candidate.candidateId,
            "name": candidate.suggestedName,
            "description": candidate.description,
            "supportCount": candidate.supportCount,
            "representativeItems": reps,
            "centerSimilarity": round(center, 4),
            "maxItemSimilarity": round(max_item, 4),
        }

    def _handle_candidate(
        self,
        item: dict[str, Any],
        item_id: str,
        ordered_scores: list[dict[str, Any]],
        classification: ItemClassification,
        log: dict[str, Any],
        ambiguous: bool,
    ) -> None:
        embedding = self.backend.embed(build_service_text(item))
        self._item_embeddings[item_id] = embedding

        sims = self._similarity_infos(embedding)
        if sims:
            top = max(sims, key=lambda s: max(s[1], s[2]))
            log["centerSimilarity"] = round(top[1], 4)
            log["maxItemSimilarity"] = round(top[2], 4)

        center_thr = self.config.center_similarity_threshold
        item_thr = self.config.item_similarity_threshold
        candidate: TemporaryCandidate | None = None
        action: str | None = None

        # 1. 임베딩 기준(centerSimilarity 또는 maxItemSimilarity) 재사용 — 확신 분류든 아니든
        #    기존 세부주제 후보와 충분히 유사하면 바로 병행 연결한다.
        eligible = [s for s in sims if s[1] >= center_thr or s[2] >= item_thr]
        if eligible:
            best = max(eligible, key=lambda s: max(s[1], s[2]))
            candidate = best[0]
            action = "REUSE_EMBEDDING"
            log["matchedExistingCandidate"] = True
        else:
            # 2. 임베딩만으로 애매 → AI가 진입 판단: REUSE(기존 후보) / CREATE(새 세부주제) / SKIP(일반 데이터)
            formal = self._formal_by_id(str(classification.formalCategoryId))
            decision = self.backend.review_candidate_entry(
                item,
                str(formal["name"]) if formal else "",
                [self._ai_candidate_info(s) for s in sims],
                formal_confident=not ambiguous,
            )
            act = str(decision.get("action", "SKIP")).upper()
            log["candidateEntryDecision"] = act
            log["candidateEntryReason"] = str(decision.get("reason", ""))
            if act == "REUSE" and decision.get("candidateId") is not None:
                picked = self._candidate_by_id(int(decision["candidateId"]))
                if picked is not None and picked.status in {PENDING, READY_TO_PROMOTE}:
                    candidate, action = picked, "REUSE_AI"
                    log["matchedExistingCandidate"] = True
            elif act == "CREATE":
                proposal = {
                    "name": decision.get("name") or f"후보-{item_id}",
                    "description": decision.get("description") or "",
                }
                candidate, created = self._create_or_reuse_candidate(item_id, embedding, proposal)
                action = "CREATE" if created else "REUSE_FINAL_DEDUP"
                log["newCandidateCreated"] = created
                log["matchedExistingCandidate"] = not created
            # act == SKIP(또는 무효 응답) → 후보 없음, 정식 카테고리에만 유지

        if candidate is None:
            return  # FORMAL_ONLY: 가장 가까운 정식 카테고리에만 표시

        log["candidateAction"] = action
        self._link_item(candidate, item_id, embedding)
        classification.candidateId = candidate.candidateId
        classification.classificationStatus = CANDIDATE_LINKED
        log["linkedCandidateId"] = candidate.candidateId
        log["candidateName"] = candidate.suggestedName
        log["candidateSupportCount"] = candidate.supportCount

        # 7~8. 승격 검토
        self._maybe_promote(candidate, log)

    def _create_or_reuse_candidate(
        self, item_id: str, embedding: list[float], proposal: dict[str, Any]
    ) -> tuple[TemporaryCandidate, bool]:
        """신규 제안을 생성 직전에 기존 후보 전체와 마지막으로 비교한다.

        반환: (후보, 새로 생성했는지)
        """
        name = normalize_category_name(proposal.get("name") or f"후보-{item_id}")
        # 이름 정규화가 완전히 같은 후보는 재사용(중복 생성 방지)
        for candidate in self._active_candidates():
            if category_key(candidate.suggestedName) == category_key(name):
                return candidate, False
        # 대표 임베딩이 매우 유사한 후보가 이미 있으면 병합 대상 → 재사용
        for candidate in self._active_candidates():
            if cosine_similarity(embedding, candidate.representativeEmbedding) >= self.merge_threshold:
                return candidate, False
        now = self._now().isoformat()
        candidate = TemporaryCandidate(
            candidateId=self._next_candidate_id,
            workspaceId=self.workspace_id,
            suggestedName=name,
            description=str(proposal.get("description") or f"{name} 관련 후보"),
            status=PENDING,
            supportCount=0,
            representativeEmbedding=list(embedding),
            createdAt=now,
            updatedAt=now,
            createdAtItemId=item_id,
            linkedItemIds=[],
            sumEmbedding=[0.0] * len(embedding),
        )
        self._next_candidate_id += 1
        self.candidates.append(candidate)
        return candidate, True

    def _link_item(
        self, candidate: TemporaryCandidate, item_id: str, embedding: list[float]
    ) -> None:
        if item_id in candidate.linkedItemIds:
            return  # 같은 데이터 중복 연결 방지
        self._item_embeddings.setdefault(item_id, embedding)
        similarity = cosine_similarity(embedding, candidate.representativeEmbedding)
        candidate.linkedItemIds.append(item_id)
        if not candidate.sumEmbedding:
            candidate.sumEmbedding = [0.0] * len(embedding)
        candidate.sumEmbedding = [a + b for a, b in zip(candidate.sumEmbedding, embedding)]
        candidate.representativeEmbedding = l2_normalize(
            [value / len(candidate.linkedItemIds) for value in candidate.sumEmbedding]
        )
        candidate.supportCount = len(candidate.linkedItemIds)
        candidate.updatedAt = self._now().isoformat()
        self.links.append(
            CandidateItemLink(candidate.candidateId, item_id, round(similarity, 4))
        )

    def merge_candidates(self, keep_id: int, drop_id: int) -> None:
        """의미가 같은 후보를 병합한다. drop 후보는 MERGED 상태가 된다."""
        with self._lock:
            keep = self._candidate_by_id(keep_id)
            drop = self._candidate_by_id(drop_id)
            if keep is None or drop is None or keep is drop:
                return
            for item_id in list(drop.linkedItemIds):
                embedding = self.backend.embed(build_service_text(self._items[item_id]))
                self._link_item(keep, item_id, embedding)
                self.item_classifications[item_id].candidateId = keep.candidateId
            drop.status = MERGED
            drop.mergedIntoCandidateId = keep.candidateId
            drop.updatedAt = self._now().isoformat()

    def _maybe_promote(self, candidate: TemporaryCandidate, log: dict[str, Any]) -> None:
        if candidate.supportCount < self.config.candidate_min_support_count:
            return
        # 승격 직전 최신 정식 카테고리 수를 다시 확인한다(동시성 방어).
        at_capacity = (
            len(self.formal_categories) >= self.config.max_count
            or self.promoted_count() >= self.config.max_ai_generated_count
        )
        if at_capacity:
            candidate.status = READY_TO_PROMOTE
            candidate.lastReviewReason = "정식 카테고리 상한으로 승격 대기"
            return
        linked_items = [self._items[item_id] for item_id in candidate.linkedItemIds]
        review = self.backend.review_promotion(candidate, linked_items)
        candidate.lastReviewReason = str(review.get("reason", ""))
        if not review.get("promote"):
            # 일관성이 약하면 보류(PENDING 유지). 명시적 거부만 REJECTED 처리는 별도 API로.
            return
        self._promote(candidate, log)

    def _promote(self, candidate: TemporaryCandidate, log: dict[str, Any]) -> None:
        # 같은 이름의 정식 카테고리가 이미 있으면 새로 만들지 않고 그쪽으로 합친다.
        key = category_key(candidate.suggestedName)
        existing = next(
            (c for c in self.formal_categories if category_key(c["name"]) == key), None
        )
        if existing is not None:
            category_id = existing["id"]
            formal = existing
        else:
            category_id = generated_category_id(candidate.suggestedName)
            if self._formal_by_id(category_id) is not None:
                category_id = f"{category_id}-{candidate.candidateId}"
            formal = {
                "id": category_id,
                "name": candidate.suggestedName,
                "description": candidate.description,
                "examples": [],
                "origin": PROMOTED_ORIGIN,
                "createdAtItemId": candidate.createdAtItemId,
                "promotedFromCandidateId": candidate.candidateId,
                "itemIds": [],
            }
            self.formal_categories.append(formal)
        candidate.status = PROMOTED
        candidate.promotedFormalCategoryId = category_id
        candidate.updatedAt = self._now().isoformat()
        # 8. 연결된 데이터를 새 정식 카테고리로 재분류
        for item_id in candidate.linkedItemIds:
            classification = self.item_classifications[item_id]
            previous = self._formal_by_id(classification.formalCategoryId)
            if previous is not None and item_id in previous["itemIds"]:
                previous["itemIds"].remove(item_id)
            classification.formalCategoryId = category_id
            # 임시 배치했던 정식 카테고리를 새 카테고리로 교체(다중 분류는 최대 2개 유지)
            new_ids = [category_id] + [
                cid for cid in classification.formalCategoryIds if cid != classification.formalCategoryId
            ]
            classification.formalCategoryIds = _dedupe_keep_order(new_ids)[
                : self.config.service_max_categories
            ]
            classification.classificationStatus = CANDIDATE_LINKED
            formal["itemIds"].append(item_id)
            self.reclassified_item_ids.add(item_id)
        log["promoted"] = True
        log["reclassified"] = True
        log["promotedFormalCategoryId"] = category_id

    # ---- 직렬화 ----

    def _formal_snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "id": category["id"],
                "name": category["name"],
                "description": category["description"],
                "examples": category["examples"],
                "origin": category["origin"],
            }
            for category in self.formal_categories
        ]

    def _log_for(self, item_id: str, *, note: str) -> dict[str, Any]:
        classification = self.item_classifications[item_id]
        return {
            "itemId": item_id,
            "note": note,
            "selectedFormalCategoryId": classification.formalCategoryId,
            "linkedCandidateId": classification.candidateId,
            "formalCategoryCount": len(self.formal_categories),
            "candidateCount": len(self._active_candidates()),
        }

    def snapshot(self) -> dict[str, Any]:
        """현재 상태 전체를 직렬화(대표 임베딩 원본 제외)."""
        return {
            "workspaceId": self.workspace_id,
            "formalCategories": [
                {
                    "id": category["id"],
                    "name": category["name"],
                    "description": category["description"],
                    "origin": category["origin"],
                    "createdAtItemId": category["createdAtItemId"],
                    "itemCount": len(category["itemIds"]),
                    "itemIds": list(category["itemIds"]),
                }
                for category in self.formal_categories
            ],
            "candidates": [candidate.public_dict() for candidate in self.candidates],
            "links": [
                {"candidateId": link.candidateId, "itemId": link.itemId, "similarity": link.similarity}
                for link in self.links
            ],
            "itemClassifications": [
                {
                    "itemId": entry.itemId,
                    "formalCategoryId": entry.formalCategoryId,
                    "formalCategoryIds": entry.formalCategoryIds,
                    "candidateId": entry.candidateId,
                    "classificationStatus": entry.classificationStatus,
                }
                for entry in self.item_classifications.values()
            ],
        }


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def summarize_run(engine: WorkspaceCategoryEngine) -> dict[str, Any]:
    """완료 기준 보고서에 필요한 지표를 계산한다."""
    formal = engine.formal_categories
    candidates = engine.candidates
    promoted = [c for c in candidates if c.status == PROMOTED]
    ready = [c for c in candidates if c.status == READY_TO_PROMOTE]
    merged = [c for c in candidates if c.status == MERGED]
    created = [c for c in candidates if c.status != MERGED]
    single_link = [c for c in candidates if c.supportCount == 1 and c.status != MERGED]
    reuse_events = sum(1 for log in engine.history if log.get("matchedExistingCandidate"))
    new_events = sum(1 for log in engine.history if log.get("newCandidateCreated"))
    return {
        "finalFormalCategoryCount": len(formal),
        "aiPromotedCategoryCount": engine.promoted_count(),
        "createdCandidateCount": len(created),
        "reusedCandidateEventCount": reuse_events,
        "newCandidateEventCount": new_events,
        "promotedCandidateCount": len(promoted),
        "readyToPromoteCandidateCount": len(ready),
        "mergedCandidateCount": len(merged),
        "singleLinkCandidateCount": len(single_link),
        "reclassifiedItemCount": len(engine.reclassified_item_ids),
        "exceededMaxFormalCategories": len(formal) > engine.config.max_count,
        "totalItems": len(engine.item_classifications),
    }
