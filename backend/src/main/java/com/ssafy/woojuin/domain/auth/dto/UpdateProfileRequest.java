package com.ssafy.woojuin.domain.auth.dto;

import com.ssafy.woojuin.domain.auth.entity.AvatarColor;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record UpdateProfileRequest(
        @NotBlank(message = "닉네임은 필수입니다") @Size(max = 50, message = "닉네임은 50자를 넘을 수 없습니다") String nickname,
        String profileImageUrl,
        AvatarColor avatarColor) {
}
