package com.ssafy.woojuin.domain.auth.jwt;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class JwtTokenProviderTest {

    private static final String TEST_SECRET = "test-secret-key-for-jwt-unit-test-1234";

    private JwtTokenProvider tokenProvider;

    @BeforeEach
    void setUp() {
        tokenProvider = new JwtTokenProvider(new JwtProperties(TEST_SECRET, 3_600_000L, 1_209_600_000L));
    }

    @Test
    @DisplayName("access token 발급 후 getUserId로 userId를 복원할 수 있다")
    void createAccessToken_thenGetUserId_returnsSameUserId() {
        String token = tokenProvider.createAccessToken(1L);

        assertThat(tokenProvider.getUserId(token)).isEqualTo(1L);
    }

    @Test
    @DisplayName("refresh token 발급 후 getUserId로 userId를 복원할 수 있다")
    void createRefreshToken_thenGetUserId_returnsSameUserId() {
        String token = tokenProvider.createRefreshToken(42L);

        assertThat(tokenProvider.getUserId(token)).isEqualTo(42L);
    }

    @Test
    @DisplayName("정상 발급된 토큰은 유효하다")
    void validateToken_validToken_returnsTrue() {
        String token = tokenProvider.createAccessToken(1L);

        assertThat(tokenProvider.validateToken(token)).isTrue();
    }

    @Test
    @DisplayName("만료된 토큰은 유효하지 않다")
    void validateToken_expiredToken_returnsFalse() {
        JwtTokenProvider expiredTokenProvider =
                new JwtTokenProvider(new JwtProperties(TEST_SECRET, -1000L, -1000L));
        String token = expiredTokenProvider.createAccessToken(1L);

        assertThat(tokenProvider.validateToken(token)).isFalse();
    }

    @Test
    @DisplayName("다른 키로 서명된 토큰은 유효하지 않다")
    void validateToken_differentSecret_returnsFalse() {
        JwtTokenProvider otherTokenProvider = new JwtTokenProvider(
                new JwtProperties("other-secret-key-for-jwt-unit-test-5678", 3_600_000L, 1_209_600_000L));
        String token = otherTokenProvider.createAccessToken(1L);

        assertThat(tokenProvider.validateToken(token)).isFalse();
    }

    @Test
    @DisplayName("형식이 잘못된 문자열은 유효하지 않다")
    void validateToken_malformedToken_returnsFalse() {
        assertThat(tokenProvider.validateToken("not-a-jwt")).isFalse();
    }
}
