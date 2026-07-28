package com.ssafy.woojuin.domain.item.dto;

import com.ssafy.woojuin.domain.category.dto.CategoryResponse;
import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.domain.item.entity.ItemType;
import com.ssafy.woojuin.global.common.ItemStatus;
import java.time.OffsetDateTime;
import java.util.List;

/**
 * 아이템 상세 응답. 목록({@link ItemSummaryResponse})에 본문 전문(content)을 더한 형태다.
 * summary는 AI 요약(본문이 있을 때만), categories는 연결된 카테고리(AI 분류 + 사용자 지정),
 * imageUrl은 IMAGE 원본 presigned URL(IMAGE 아닐 시 null)이다.
 */
public record ItemDetailResponse(
        Long itemId,
        ItemType type,
        ItemStatus status,
        String title,
        String url,
        String content,
        String summary,
        ItemPreview preview,
        String imageUrl,
        List<CategoryResponse> categories,
        boolean favorite,
        OffsetDateTime createdAt,
        OffsetDateTime deletedAt) {

    public static ItemDetailResponse from(Item item, List<CategoryResponse> categories, String imageUrl) {
        return new ItemDetailResponse(
                item.getId(),
                item.getType(),
                item.getStatus(),
                item.getTitle(),
                item.getUrl(),
                item.getContent(),
                item.getSummary(),
                ItemPreview.from(item),
                imageUrl,
                categories,
                item.isFavorite(),
                item.getCreatedAt(),
                item.getDeletedAt());
    }
}
