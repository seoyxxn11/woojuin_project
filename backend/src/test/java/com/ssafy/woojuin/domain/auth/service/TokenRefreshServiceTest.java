package com.ssafy.woojuin.domain.auth.service;

import com.ssafy.woojuin.domain.auth.dto.TokenResponse;
import com.ssafy.woojuin.domain.auth.jwt.JwtTokenProvider;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TokenRefreshServiceTest {

    @Mock
    private JwtTokenProvider jwtTokenProvider;

    @Mock
    private RefreshTokenStore refreshTokenStore;

    @InjectMocks
    private TokenRefreshService tokenRefreshService;

    @Test
    @DisplayName("저장된 것과 일치하는 유효한 refresh token이면 새 access token을 발급한다")
    void refresh_validAndMatchingToken_returnsNewAccessToken() {
        when(jwtTokenProvider.validateToken("refresh-token-value")).thenReturn(true);
        when(jwtTokenProvider.getUserId("refresh-token-value")).thenReturn(1L);
        when(refreshTokenStore.findByUserId(1L)).thenReturn(Optional.of("refresh-token-value"));
        when(jwtTokenProvider.createAccessToken(1L)).thenReturn("new-access-token");

        TokenResponse response = tokenRefreshService.refresh("refresh-token-value");

        assertThat(response.accessToken()).isEqualTo("new-access-token");
        assertThat(response.refreshToken()).isEqualTo("refresh-token-value");
    }

    @Test
    @DisplayName("유효하지 않은(만료/위조) refresh token이면 예외를 던진다")
    void refresh_invalidToken_throwsException() {
        when(jwtTokenProvider.validateToken("bad-token")).thenReturn(false);

        assertThatThrownBy(() -> tokenRefreshService.refresh("bad-token"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    @DisplayName("Redis에 저장된 refresh token이 없으면(로그아웃 등) 예외를 던진다")
    void refresh_noStoredToken_throwsException() {
        when(jwtTokenProvider.validateToken("refresh-token-value")).thenReturn(true);
        when(jwtTokenProvider.getUserId("refresh-token-value")).thenReturn(1L);
        when(refreshTokenStore.findByUserId(1L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> tokenRefreshService.refresh("refresh-token-value"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    @DisplayName("저장된 refresh token과 값이 다르면 예외를 던진다")
    void refresh_tokenMismatch_throwsException() {
        when(jwtTokenProvider.validateToken("old-refresh-token")).thenReturn(true);
        when(jwtTokenProvider.getUserId("old-refresh-token")).thenReturn(1L);
        when(refreshTokenStore.findByUserId(1L)).thenReturn(Optional.of("newer-refresh-token"));

        assertThatThrownBy(() -> tokenRefreshService.refresh("old-refresh-token"))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
