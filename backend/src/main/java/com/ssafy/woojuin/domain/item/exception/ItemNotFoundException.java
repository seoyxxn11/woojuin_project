package com.ssafy.woojuin.domain.item.exception;

public class ItemNotFoundException extends RuntimeException {

    public ItemNotFoundException(Long itemId) {
        super("COMMON_404: 아이템을 찾을 수 없습니다 (id=" + itemId + ")");
    }
}
