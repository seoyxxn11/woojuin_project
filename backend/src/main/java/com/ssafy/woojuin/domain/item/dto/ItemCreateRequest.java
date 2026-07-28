package com.ssafy.woojuin.domain.item.dto;

import com.ssafy.woojuin.domain.item.entity.ItemType;
import jakarta.validation.constraints.NotNull;

/**
 * URL/MEMO 저장 요청 (JSON). IMAGE는 multipart/form-data로 별도 처리한다.
 */
public record ItemCreateRequest(
        @NotNull ItemType type,
        String url,
        String content) {
}
