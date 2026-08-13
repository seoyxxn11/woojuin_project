package com.ssafy.woojuin.domain.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record SignupRequest(
        @NotBlank(message = "이메일은 필수입니다") @Email(message = "이메일 형식이 올바르지 않습니다") String email,
        @NotBlank(message = "비밀번호는 필수입니다") @Size(min = 8, message = "비밀번호는 8자 이상이어야 합니다") String password,
        @NotBlank(message = "닉네임은 필수입니다")
        @Size(min = 2, max = 20, message = "닉네임은 한글, 영문, 숫자로 2~20자 입력해 주세요.")
        @Pattern(regexp = "^[가-힣A-Za-z0-9]+$", message = "닉네임은 한글, 영문, 숫자로 2~20자 입력해 주세요.")
        String nickname) {
}
