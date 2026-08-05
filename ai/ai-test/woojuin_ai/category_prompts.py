"""증분 카테고리(앵커) 엔진 stateless decide용 프롬프트.

모든 프롬프트는 제목+요약만 사용한다(본문 미사용). ai-mix의 chat_json(messages, schema)
계약에 맞춰 messages 리스트를 반환한다.
"""

from __future__ import annotations

from .category_models import DecideCandidate, DecideFormalCategory, DecideItem, DecideSignal


def _item_text(item: DecideItem) -> str:
    parts = []
    if item.title:
        parts.append(str(item.title).strip())
    if item.summary:
        parts.append(str(item.summary).strip())
    return "\n".join(parts)


def formal_classify_messages(
    item: DecideItem, formal_categories: list[DecideFormalCategory]
) -> list[dict[str, str]]:
    catalog = "\n".join(f"- {c.category_id} | {c.name}" for c in formal_categories)
    content = (
        "다음 데이터가 각 카테고리에 얼마나 맞는지 0.0~1.0 점수로 평가하세요.\n"
        "모든 categoryId에 대해 점수를 매기세요.\n\n"
        f"카테고리:\n{catalog}\n\n데이터:\n{_item_text(item)}\n"
    )
    return [{"role": "user", "content": content}]


def anchor_extract_messages(item: DecideItem) -> list[dict[str, str]]:
    content = (
        "다음 데이터의 제목과 요약에서 '카테고리 앵커(categoryAnchor)' 하나를 추출하세요.\n"
        "카테고리 앵커는 개별 문서보다 한 단계 위의 공통 개념이며, 두 유형이 있습니다.\n"
        "1) ENTITY: 특정 작품·기관·브랜드·인물 (예: 짱구, SSAFY).\n"
        "   - 등장인물·에피소드·극장판·후기·모집 등 세부는 상위 작품/기관명으로 정규화.\n"
        "     예) 맹구/신짱구/짱구 극장판/크레용 신짱 → '짱구'. 싸피/삼성 청년 SW·AI 아카데미 → 'SSAFY'.\n"
        "2) UMBRELLA_TOPIC: 여러 세부 주제를 아우르는 상위 개념.\n"
        "   예) 별자리·사주·타로·띠별·토정비결 → '운세'.\n"
        "       애착 유형·행동 유형·대인관계·스트레스 대처·가치관 → '자기 이해'.\n"
        "       기록 앱·나중에 읽기·링크 관리·문서 자동 분류·자료 동기화 → '디지털 정리'.\n"
        "규칙:\n"
        "- 개별 문서보다 한 단계 위의 공통 개념을 고르되, '문화/학습/생활'처럼 기본 카테고리 수준까지 넓히지 마세요.\n"
        "- 지나치게 좁은 세부(예: '공룡의 팔')가 아니라 포괄 대상(예: '공룡')을 고르세요.\n"
        "- normalizedAnchorName은 별칭을 대표하는 짧은 표준 이름입니다.\n"
        "- specificEntities에는 이 문서가 실제로 다룬 세부 대상을 넣으세요.\n"
        "- 앵커가 뚜렷하지 않으면 categoryAnchorType을 OTHER로 하고 anchorConfidence를 낮게 주세요.\n\n"
        f"제목: {item.title or ''}\n요약: {item.summary or ''}\n"
    )
    return [{"role": "user", "content": content}]


def review_candidate_entry_messages(
    item: DecideItem, base_category_name: str, candidates: list[DecideCandidate]
) -> list[dict[str, str]]:
    lines = []
    for c in candidates:
        reps = "; ".join(
            f"{(r.title or '')}({(r.summary or '')[:40]})" for r in c.representative_items
        )
        lines.append(
            f"- candidateId={c.candidate_id} | 이름:{c.suggested_name} | 연결수:{c.support_count}"
            f" | 유사도:{c.similarity} | 대표:{reps}"
        )
    content = (
        f"데이터는 정식 카테고리 '{base_category_name}'에 이미 분류됐다.\n"
        "아래 기존 세부주제 후보 중 '같은 반복 주제'가 있으면 REUSE(candidateId)로 재사용하라.\n"
        "형식만 비슷하고 목적이 다르면 재사용하지 말고 SKIP. 새 후보 생성(CREATE)은 하지 마라(생성은 백엔드가 별도 처리).\n\n"
        f"새 데이터:\n제목: {item.title or ''}\n요약: {item.summary or ''}\n\n"
        f"기존 세부주제 후보:\n" + ("\n".join(lines) if lines else "(없음)") + "\n"
    )
    return [{"role": "user", "content": content}]


def review_signal_conversion_messages(
    item: DecideItem, signal: DecideSignal
) -> list[dict[str, str]]:
    first = signal.first_item
    content = (
        "같은 정식 카테고리에 확신 분류된 두 데이터가 있다. 이 둘이 '기존 정식 카테고리보다 구체적이고 "
        "앞으로도 반복될 세부 주제'로 묶을 가치가 있는지 판단하라. 형식만 비슷하고 목적이 다르면 convert=false.\n"
        f"예상 앵커: {signal.normalized_anchor_name or ''}\n"
        f"첫 번째 데이터: 제목 {first.title or ''} · 요약 {first.summary or ''}\n"
        f"두 번째 데이터: 제목 {item.title or ''} · 요약 {item.summary or ''}\n"
    )
    return [{"role": "user", "content": content}]


def review_promotion_messages(
    candidate_name: str, samples: list[str]
) -> list[dict[str, str]]:
    titles = "\n".join(f"- {t}" for t in samples if t)
    content = (
        "다음 데이터들이 하나의 일관된 반복 주제인지 검토하세요. 사용 목적이 제각각이거나 "
        "지나치게 넓은 일반 개념이면 승격하지 마세요.\n"
        f"후보 이름: {candidate_name}\n연결 데이터:\n{titles}\n"
    )
    return [{"role": "user", "content": content}]
