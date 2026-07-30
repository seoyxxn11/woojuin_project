package com.ssafy.woojuin.domain.item.dto;

import com.ssafy.woojuin.domain.item.entity.ItemType;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/**
 * URL/MEMO 저장 요청 (JSON). IMAGE는 multipart/form-data로 별도 처리한다.
 *
 * <p>{@code title}은 <b>OS 공유 시트가 준 제목</b>을 담는 선택 필드다(FR-013). 쿠팡처럼
 * 봇을 구조적으로 막는 쇼핑몰은 크롤링으로 제목을 얻을 수 없는데, 공유 시트는 상품명을
 * 함께 넘겨준다 — 그걸 버리지 않고 받아서 크롤링이 실패했을 때의 제목으로 쓴다.
 * IMAGE가 원본 파일명을 title 기본값으로 넣는 것과 같은 목적이다(분류 힌트 확보).
 *
 * <p>제목 우선순위는 {@code ai-mix가 다듬은 제목 > 이 필드 > OG 제목 > host+path 폴백}이다.
 * 이 필드가 OG보다 앞서는 건 {@link com.ssafy.woojuin.domain.item.entity.Item#applyPreview}가
 * title이 비어 있을 때만 채우기 때문이고, 그래도 지저분한 공유 텍스트가 그대로 남지 않는 건
 * AI 보강이 제목을 덮어쓰기 때문이다({@link com.ssafy.woojuin.domain.ai.AiAnalysis} 참고).
 *
 * <p>사용자 제어 입력이라 길이를 여기서 막는다. {@code items.title}이 500자라 넘치면 insert가
 * 터지는데, 컨트롤러에 {@code @Valid}가 붙어 있어 초과 시 500이 아니라 400이 나간다.
 */
public record ItemCreateRequest(
        @NotNull ItemType type,
        String url,
        String content,
        @Size(max = 500, message = "title은 500자를 넘을 수 없습니다") String title) {
}
