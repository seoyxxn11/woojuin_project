package com.ssafy.woojuin.domain.item.dto;

import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.global.common.ItemStatus;
import java.time.OffsetDateTime;

public record ItemCreateResponse(Long itemId, ItemStatus status, OffsetDateTime createdAt) {

    public static ItemCreateResponse from(Item item) {
        return new ItemCreateResponse(item.getId(), item.getStatus(), item.getCreatedAt());
    }
}
