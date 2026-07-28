package com.ssafy.woojuin.domain.item.dto;

import jakarta.validation.constraints.Size;

/**
 * 아이템 수정 요청. null인 필드는 수정하지 않는다(부분 수정).
 * 태그·카테고리 수정(API 명세서)은 Tag/Category 도메인이 아직 없어 이번 범위 밖.
 */
public record ItemUpdateRequest(
        @Size(max = 500, message = "제목은 500자를 넘을 수 없습니다") String title,
        String content) {
}
