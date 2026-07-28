package com.ssafy.woojuin.domain.ai;

/**
 * {@link AiAnalyzer} 임시 스텁 (묶음 F 미구현 구간용).
 *
 * <p>항상 빈 분석 결과를 돌려준다 — URL 파이프라인이 F를 기다리지 않고 트랙 B까지
 * 동작·검증되게 하려는 것. 분석 결과가 비므로 아이템은 PARTIAL로 남는다.
 *
 * <p>{@link AiAnalyzerConfig}가 {@code @ConditionalOnMissingBean}으로 등록하므로,
 * 묶음 F가 진짜 AiAnalyzer 빈을 올리면 이 스텁은 물러난다.
 */
public class NoOpAiAnalyzer implements AiAnalyzer {

    @Override
    public AiAnalysis analyze(AiAnalysisRequest request) {
        return AiAnalysis.empty();
    }
}
