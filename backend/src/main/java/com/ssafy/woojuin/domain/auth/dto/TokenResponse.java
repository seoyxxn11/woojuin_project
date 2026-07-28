package com.ssafy.woojuin.domain.auth.dto;

public record TokenResponse(String accessToken, String refreshToken) {
}
