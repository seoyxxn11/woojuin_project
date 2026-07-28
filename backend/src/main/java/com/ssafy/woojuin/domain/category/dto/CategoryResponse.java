package com.ssafy.woojuin.domain.category.dto;

import com.ssafy.woojuin.domain.category.entity.Category;

/**
 * 카테고리 응답. color는 카드/별자리 표시용 hex 색상(예 "#C9B8FF")이다.
 * 아이템 응답의 categories에도 이 형태로 포함된다.
 */
public record CategoryResponse(Long categoryId, String name, String color) {

    public static CategoryResponse from(Category category) {
        return new CategoryResponse(category.getId(), category.getName(), category.getColor());
    }
}
