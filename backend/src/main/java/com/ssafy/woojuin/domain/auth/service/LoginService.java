package com.ssafy.woojuin.domain.auth.service;

import com.ssafy.woojuin.domain.auth.dto.LoginRequest;
import com.ssafy.woojuin.domain.auth.dto.TokenResponse;
import com.ssafy.woojuin.domain.auth.jwt.JwtTokenProvider;
import com.ssafy.woojuin.domain.auth.security.CustomUserPrincipal;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Service;

@Service
public class LoginService {

    private final AuthenticationManager authenticationManager;
    private final JwtTokenProvider jwtTokenProvider;
    private final RefreshTokenStore refreshTokenStore;

    public LoginService(AuthenticationManager authenticationManager, JwtTokenProvider jwtTokenProvider,
                         RefreshTokenStore refreshTokenStore) {
        this.authenticationManager = authenticationManager;
        this.jwtTokenProvider = jwtTokenProvider;
        this.refreshTokenStore = refreshTokenStore;
    }

    public TokenResponse login(LoginRequest request) {
        Authentication authentication = authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(request.email(), request.password()));
        CustomUserPrincipal principal = (CustomUserPrincipal) authentication.getPrincipal();

        String accessToken = jwtTokenProvider.createAccessToken(principal.getUserId());
        String refreshToken = jwtTokenProvider.createRefreshToken(principal.getUserId());
        refreshTokenStore.save(principal.getUserId(), refreshToken);
        return new TokenResponse(accessToken, refreshToken);
    }
}
