package com.ssafy.woojuin.domain.auth.oauth;

import com.ssafy.woojuin.domain.auth.jwt.JwtTokenProvider;
import com.ssafy.woojuin.domain.auth.service.RefreshTokenStore;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.security.web.authentication.AuthenticationSuccessHandler;
import org.springframework.security.web.authentication.logout.SecurityContextLogoutHandler;
import org.springframework.stereotype.Component;
import org.springframework.web.util.UriComponentsBuilder;

import java.io.IOException;

@Component
public class OAuth2LoginSuccessHandler implements AuthenticationSuccessHandler {

    private final JwtTokenProvider jwtTokenProvider;
    private final RefreshTokenStore refreshTokenStore;
    private final String redirectBaseUrl;

    public OAuth2LoginSuccessHandler(JwtTokenProvider jwtTokenProvider, RefreshTokenStore refreshTokenStore,
                                      @Value("${woojuin.oauth.redirect-base-url}") String redirectBaseUrl) {
        this.jwtTokenProvider = jwtTokenProvider;
        this.refreshTokenStore = refreshTokenStore;
        this.redirectBaseUrl = redirectBaseUrl;
    }

    @Override
    public void onAuthenticationSuccess(HttpServletRequest request, HttpServletResponse response,
                                         Authentication authentication) throws IOException, ServletException {
        Long userId = ((CustomOidcUser) authentication.getPrincipal()).getUserId();

        String accessToken = jwtTokenProvider.createAccessToken(userId);
        String refreshToken = jwtTokenProvider.createRefreshToken(userId);
        refreshTokenStore.save(userId, refreshToken);

        // oauth2Login()은 인가 요청을 세션에 담아 처리하는데, 로그인 이후 우리는
        // JWT로만 인증하므로 이 세션을 계속 살려두면 JWT 없이도 세션 쿠키만으로
        // 인증된 것처럼 남는 부작용이 생긴다. 토큰 발급 직후 바로 정리한다.
        new SecurityContextLogoutHandler().logout(request, response, authentication);

        String redirectUrl = UriComponentsBuilder.fromUriString(redirectBaseUrl)
                .queryParam("accessToken", accessToken)
                .queryParam("refreshToken", refreshToken)
                .build()
                .toUriString();

        response.sendRedirect(redirectUrl);
    }
}
