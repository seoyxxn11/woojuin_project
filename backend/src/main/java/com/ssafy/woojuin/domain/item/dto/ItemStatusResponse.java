package com.ssafy.woojuin.domain.item.dto;

import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.global.common.ItemStatus;

public record ItemStatusResponse(Long itemId, ItemStatus status) {

    public static ItemStatusResponse from(Item item) {
        return new ItemStatusResponse(item.getId(), item.getStatus());
    }
}
