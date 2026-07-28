package com.ssafy.woojuin.global.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.woojuin.global.common.ApiResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.MediaType;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.stereotype.Component;

import java.io.IOException;

/**
 * oauth2Login()의 기본 AuthenticationEntryPoint는 등록된 provider가 하나뿐이면
 * 인증 실패 시 곧장 그 provider(구글)로 리다이렉트한다. REST API는 리다이렉트가
 * 아니라 401 JSON을 받아야 하므로 엔트리 포인트를 이걸로 교체한다.
 * (/oauth2/authorization/google 자체는 프론트가 직접 이동하는 경로라 영향 없음)
 */
@Component
public class RestAuthenticationEntryPoint implements AuthenticationEntryPoint {

    private final ObjectMapper objectMapper;

    public RestAuthenticationEntryPoint(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @Override
    public void commence(HttpServletRequest request, HttpServletResponse response,
                          AuthenticationException authException) throws IOException {
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setCharacterEncoding("UTF-8");
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.getWriter().write(objectMapper.writeValueAsString(ApiResponse.of(401, "인증이 필요합니다", null)));
    }
}
