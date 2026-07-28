package com.ssafy.woojuin.domain.item.processing.image;

import com.sksamuel.scrimage.ImmutableImage;
import com.sksamuel.scrimage.webp.WebpWriter;
import org.springframework.stereotype.Component;

/**
 * IMAGE 원본 바이트 → 목록 카드용 저용량 webp 썸네일. 긴 변 200px 이내로 비율을 유지해
 * 축소하고 webp(품질 80)로 인코딩한다 — 목록은 이미지를 작게 보여주므로 원본을 그대로
 * 내려받게 하는 것보다 바이트가 훨씬 작아 로딩이 빠르다.
 *
 * <p>scrimage-webp는 인코딩에 번들 네이티브 바이너리(libwebp)를 사용한다. 생성이 실패하면
 * (지원 안 되는 환경/깨진 이미지 등) 예외를 던지고, 호출부(ImageItemProcessor)가 이를
 * 흡수해 썸네일 없이 원본 폴백으로 진행한다 — 썸네일은 최적화지 필수 경로가 아니다.
 */
@Component
public class ImageThumbnailGenerator {

    private static final int MAX_EDGE = 200;
    private static final int QUALITY = 80;

    public byte[] toThumbnail(byte[] original) {
        try {
            return ImmutableImage.loader().fromBytes(original)
                    .max(MAX_EDGE, MAX_EDGE)
                    .bytes(WebpWriter.DEFAULT.withQ(QUALITY));
        } catch (Exception e) {
            throw new IllegalStateException("썸네일 생성 실패", e);
        }
    }
}
