package com.ssafy.woojuin.domain.item.dto;

import com.ssafy.woojuin.domain.item.entity.Item;

/**
 * URL 아이템 미리보기(트랙 A) 결과. thumbnailUrl은 oEmbed/OpenGraph에서 얻은 대표
 * 이미지, description은 페이지 메타데이터(og:description 등)다 — AI 요약(summary)과 달리
 * 본문/AI 없이도 채워지므로 요약이 없는 아이템의 설명 폴백으로 쓸 수 있다.
 * 목록·상세 응답이 공유한다.
 */
public record ItemPreview(String thumbnailUrl, String description) {

    public static ItemPreview from(Item item) {
        return new ItemPreview(item.getPreviewThumbnailUrl(), item.getPreviewDescription());
    }
}
