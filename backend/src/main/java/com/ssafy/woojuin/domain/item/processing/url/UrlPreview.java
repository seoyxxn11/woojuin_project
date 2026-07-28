package com.ssafy.woojuin.domain.item.processing.url;

/**
 * 트랙 A 산출물 — 미리보기 카드에 쓸 메타데이터.
 * oEmbed/OG 스크래핑 결과가 이 형태로 수렴한다. 확보 못 한 필드는 null.
 */
public record UrlPreview(String title, String thumbnailUrl, String description) {

    public static UrlPreview empty() {
        return new UrlPreview(null, null, null);
    }

    /** title조차 못 얻었으면 미리보기 카드로서 의미가 없다 → 트랙 A 실패로 본다. */
    public boolean hasNothing() {
        return (title == null || title.isBlank())
                && (thumbnailUrl == null || thumbnailUrl.isBlank())
                && (description == null || description.isBlank());
    }
}
