package com.ssafy.woojuin.domain.item.processing.image;

/**
 * {@link ImageTextExtractor} 임시 스텁 (묶음 F 미구현 구간용).
 *
 * <p>항상 null을 돌려준다 — IMAGE 파이프라인이 F(OCR)를 기다리지 않고 큐 소비·
 * AI 보강·상태 확정까지 동작·검증되게 하려는 것. 텍스트가 없으므로 아이템은
 * PARTIAL로 남는다.
 *
 * <p>{@link ImageTextExtractorConfig}가 {@code @ConditionalOnMissingBean}으로
 * 등록하므로, 묶음 F가 진짜 ImageTextExtractor 빈을 올리면 이 스텁은 물러난다.
 */
public class NoOpImageTextExtractor implements ImageTextExtractor {

    @Override
    public String extract(byte[] imageBytes) {
        return null;
    }
}
