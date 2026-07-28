package com.ssafy.woojuin.domain.auth.jwt;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "woojuin.jwt")
public record JwtProperties(String secret, long accessTokenValidity, long refreshTokenValidity) {
}
