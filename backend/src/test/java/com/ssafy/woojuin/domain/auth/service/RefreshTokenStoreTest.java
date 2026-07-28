package com.ssafy.woojuin.domain.auth.service;

import com.ssafy.woojuin.domain.auth.jwt.JwtProperties;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

import java.time.Duration;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class RefreshTokenStoreTest {

    private static final JwtProperties PROPERTIES = new JwtProperties("test-secret", 3_600_000L, 1_209_600_000L);

    @Mock
    private StringRedisTemplate redisTemplate;

    @Mock
    private ValueOperations<String, String> valueOperations;

    private RefreshTokenStore refreshTokenStore;

    @Test
    @DisplayName("save는 refresh-token:{userId} 키로 만료시간(refreshTokenValidity)과 함께 저장한다")
    void save_storesTokenWithUserIdKeyAndTtl() {
        refreshTokenStore = new RefreshTokenStore(redisTemplate, PROPERTIES);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);

        refreshTokenStore.save(1L, "refresh-token-value");

        verify(valueOperations).set("refresh-token:1", "refresh-token-value", Duration.ofMillis(1_209_600_000L));
    }

    @Test
    @DisplayName("findByUserId는 저장된 토큰을 반환한다")
    void findByUserId_existingKey_returnsToken() {
        refreshTokenStore = new RefreshTokenStore(redisTemplate, PROPERTIES);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("refresh-token:1")).thenReturn("refresh-token-value");

        Optional<String> result = refreshTokenStore.findByUserId(1L);

        assertThat(result).contains("refresh-token-value");
    }

    @Test
    @DisplayName("findByUserId는 저장된 게 없으면 빈 값을 반환한다")
    void findByUserId_missingKey_returnsEmpty() {
        refreshTokenStore = new RefreshTokenStore(redisTemplate, PROPERTIES);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("refresh-token:1")).thenReturn(null);

        Optional<String> result = refreshTokenStore.findByUserId(1L);

        assertThat(result).isEmpty();
    }

    @Test
    @DisplayName("delete는 refresh-token:{userId} 키를 삭제한다")
    void delete_removesKey() {
        refreshTokenStore = new RefreshTokenStore(redisTemplate, PROPERTIES);

        refreshTokenStore.delete(1L);

        verify(redisTemplate).delete("refresh-token:1");
    }
}
