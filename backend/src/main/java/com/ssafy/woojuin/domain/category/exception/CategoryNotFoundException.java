package com.ssafy.woojuin.domain.category.exception;

/** 카테고리가 없거나 다른 워크스페이스 소속이라 접근할 수 없을 때. */
public class CategoryNotFoundException extends RuntimeException {

    public CategoryNotFoundException(Long categoryId) {
        super("카테고리를 찾을 수 없습니다: " + categoryId);
    }
}
