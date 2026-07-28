package com.ssafy.woojuin.domain.auth.service;

import org.springframework.stereotype.Service;

@Service
public class LogoutService {

    private final RefreshTokenStore refreshTokenStore;

    public LogoutService(RefreshTokenStore refreshTokenStore) {
        this.refreshTokenStore = refreshTokenStore;
    }

    public void logout(Long userId) {
        refreshTokenStore.delete(userId);
    }
}
