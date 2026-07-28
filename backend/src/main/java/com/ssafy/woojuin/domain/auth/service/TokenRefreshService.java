package com.ssafy.woojuin.domain.auth.service;

import com.ssafy.woojuin.domain.auth.dto.TokenResponse;
import com.ssafy.woojuin.domain.auth.jwt.JwtTokenProvider;
import org.springframework.stereotype.Service;

@Service
public class TokenRefreshService {

    private final JwtTokenProvider jwtTokenProvider;
    private final RefreshTokenStore refreshTokenStore;

    public TokenRefreshService(JwtTokenProvider jwtTokenProvider, RefreshTokenStore refreshTokenStore) {
        this.jwtTokenProvider = jwtTokenProvider;
        this.refreshTokenStore = refreshTokenStore;
    }

    public TokenResponse refresh(String refreshToken) {
        if (!jwtTokenProvider.validateToken(refreshToken)) {
            throw new IllegalArgumentException("유효하지 않은 refresh token입니다");
        }

        Long userId = jwtTokenProvider.getUserId(refreshToken);
        String storedToken = refreshTokenStore.findByUserId(userId)
                .orElseThrow(() -> new IllegalArgumentException("저장된 refresh token이 없습니다"));
        if (!storedToken.equals(refreshToken)) {
            throw new IllegalArgumentException("refresh token이 일치하지 않습니다");
        }

        String newAccessToken = jwtTokenProvider.createAccessToken(userId);
        return new TokenResponse(newAccessToken, refreshToken);
    }
}
