package com.ssafy.woojuin.domain.auth.service;

import com.ssafy.woojuin.domain.auth.dto.LoginRequest;
import com.ssafy.woojuin.domain.auth.dto.TokenResponse;
import com.ssafy.woojuin.domain.auth.entity.AuthProvider;
import com.ssafy.woojuin.domain.auth.entity.User;
import com.ssafy.woojuin.domain.auth.jwt.JwtTokenProvider;
import com.ssafy.woojuin.domain.auth.security.CustomUserPrincipal;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.test.util.ReflectionTestUtils;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class LoginServiceTest {

    @Mock
    private AuthenticationManager authenticationManager;

    @Mock
    private JwtTokenProvider jwtTokenProvider;

    @Mock
    private RefreshTokenStore refreshTokenStore;

    private LoginService loginService;

    @Test
    @DisplayName("인증에 성공하면 access/refresh 토큰을 발급하고 refresh token을 저장한다")
    void login_validCredentials_returnsTokenPair() {
        loginService = new LoginService(authenticationManager, jwtTokenProvider, refreshTokenStore);
        User user = User.builder()
                .email("test@woojuin.com")
                .passwordHash("encoded-password")
                .provider(AuthProvider.LOCAL)
                .emailVerified(true)
                .nickname("우주인")
                .build();
        ReflectionTestUtils.setField(user, "id", 1L);
        CustomUserPrincipal principal = new CustomUserPrincipal(user);

        when(authenticationManager.authenticate(any())).thenReturn(
                new UsernamePasswordAuthenticationToken(principal, null, principal.getAuthorities()));
        when(jwtTokenProvider.createAccessToken(1L)).thenReturn("access-token");
        when(jwtTokenProvider.createRefreshToken(1L)).thenReturn("refresh-token");

        TokenResponse response = loginService.login(new LoginRequest("test@woojuin.com", "raw-password"));

        assertThat(response.accessToken()).isEqualTo("access-token");
        assertThat(response.refreshToken()).isEqualTo("refresh-token");
        verify(refreshTokenStore).save(1L, "refresh-token");
    }

    @Test
    @DisplayName("인증에 실패하면 예외가 그대로 전파된다")
    void login_invalidCredentials_propagatesException() {
        loginService = new LoginService(authenticationManager, jwtTokenProvider, refreshTokenStore);
        when(authenticationManager.authenticate(any())).thenThrow(new BadCredentialsException("bad credentials"));

        assertThatThrownBy(() -> loginService.login(new LoginRequest("test@woojuin.com", "wrong-password")))
                .isInstanceOf(BadCredentialsException.class);
    }
}
