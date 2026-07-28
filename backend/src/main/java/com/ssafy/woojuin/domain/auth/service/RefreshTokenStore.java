package com.ssafy.woojuin.domain.auth.service;

import com.ssafy.woojuin.domain.auth.jwt.JwtProperties;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.Optional;

/**
 * refresh token은 RDB 테이블 없이 Redis에 userId 기준으로 저장한다 (ERD 설계 노트).
 * 새 로그인 시 덮어쓰기 = 이전 refresh token은 자연히 무효화된다.
 */
@Component
public class RefreshTokenStore {

    static final String KEY_PREFIX = "refresh-token:";

    private final StringRedisTemplate redisTemplate;
    private final JwtProperties jwtProperties;

    public RefreshTokenStore(StringRedisTemplate redisTemplate, JwtProperties jwtProperties) {
        this.redisTemplate = redisTemplate;
        this.jwtProperties = jwtProperties;
    }

    public void save(Long userId, String refreshToken) {
        redisTemplate.opsForValue()
                .set(KEY_PREFIX + userId, refreshToken, Duration.ofMillis(jwtProperties.refreshTokenValidity()));
    }

    public Optional<String> findByUserId(Long userId) {
        return Optional.ofNullable(redisTemplate.opsForValue().get(KEY_PREFIX + userId));
    }

    public void delete(Long userId) {
        redisTemplate.delete(KEY_PREFIX + userId);
    }
}
