package com.ssafy.woojuin.domain.category.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record CategoryCreateRequest(
        @NotBlank @Size(max = 50) String name) {
}
