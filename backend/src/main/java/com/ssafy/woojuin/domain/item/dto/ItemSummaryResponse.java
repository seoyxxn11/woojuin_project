package com.ssafy.woojuin.domain.item.dto;

import com.ssafy.woojuin.domain.category.dto.CategoryResponse;
import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.domain.item.entity.ItemType;
import com.ssafy.woojuin.global.common.ItemStatus;
import java.time.OffsetDateTime;
import java.util.List;

/**
 * 목록/휴지통 카드용 응답. 상세({@link ItemDetailResponse})에서 본문 전문(content)만 뺀
 * 형태다 — 카드엔 본문이 필요 없고, text 컬럼이 목록 N건에 실리면 페이로드가 커지기 때문.
 * 카드 설명은 summary가 있으면 summary를, 없으면 preview.description을 쓰는 폴백을 상정한다.
 * imageUrl은 IMAGE 원본 presigned URL(IMAGE 아닐 시 null)이다.
 */
public record ItemSummaryResponse(
        Long itemId,
        ItemType type,
        ItemStatus status,
        String title,
        String url,
        String summary,
        ItemPreview preview,
        String imageUrl,
        List<CategoryResponse> categories,
        boolean favorite,
        OffsetDateTime createdAt,
        OffsetDateTime deletedAt) {

    public static ItemSummaryResponse from(Item item, List<CategoryResponse> categories, String imageUrl) {
        return new ItemSummaryResponse(
                item.getId(),
                item.getType(),
                item.getStatus(),
                item.getTitle(),
                item.getUrl(),
                item.getSummary(),
                ItemPreview.from(item),
                imageUrl,
                categories,
                item.isFavorite(),
                item.getCreatedAt(),
                item.getDeletedAt());
    }
}
