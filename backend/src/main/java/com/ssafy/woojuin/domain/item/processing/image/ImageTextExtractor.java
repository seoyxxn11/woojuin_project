package com.ssafy.woojuin.domain.item.processing.image;

/**
 * 이미지 바이트 → 텍스트(OCR). 묶음 F 담당.
 *
 * <p>이미지에서 "어떻게 텍스트를 얻는가"는 IMAGE 파이프라인 전용 단계라
 * {@link com.ssafy.woojuin.domain.ai.AiAnalyzer}와는 별도 인터페이스로 분리한다
 * (URL의 {@code ContentExtractor}가 url 패키지에 있는 것과 동일 논리). 추출된
 * 텍스트는 {@link com.ssafy.woojuin.domain.ai.AiAnalysisRequest}의 text로 들어가
 * 요약·분류 대상이 된다.
 *
 * <p>구현체는 실패하거나 텍스트가 없으면 예외 대신 null을 반환할 것.
 */
public interface ImageTextExtractor {

    String extract(byte[] imageBytes);
}
