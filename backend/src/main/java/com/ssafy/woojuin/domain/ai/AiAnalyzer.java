package com.ssafy.woojuin.domain.ai;

/**
 * 텍스트 → 요약·카테고리·태그. 묶음 F 담당.
 *
 * <p>URL(묶음 D)·이미지·메모가 공유하는 단일 진입점이다. 각 타입은 "어떻게 텍스트를
 * 얻는가"만 다르고, 그 뒤 분석은 전부 여기로 모인다.
 *
 * <p>구현체는 실패 시 예외를 던지지 말고 {@link AiAnalysis#empty()}를 반환할 것.
 * AI 실패가 이미 확보한 미리보기·본문까지 날리면 안 되기 때문이다.
 */
public interface AiAnalyzer {

    AiAnalysis analyze(AiAnalysisRequest request);
}
