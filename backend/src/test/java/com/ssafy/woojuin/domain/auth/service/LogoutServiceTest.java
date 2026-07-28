package com.ssafy.woojuin.domain.auth.service;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.mockito.Mockito.verify;

@ExtendWith(MockitoExtension.class)
class   LogoutServiceTest {

    @Mock
    private RefreshTokenStore refreshTokenStore;

    @InjectMocks
    private LogoutService logoutService;

    @Test
    @DisplayName("로그아웃하면 저장된 refresh token을 삭제한다")
    void logout_deletesStoredRefreshToken() {
        logoutService.logout(1L);

        verify(refreshTokenStore).delete(1L);
    }
}
