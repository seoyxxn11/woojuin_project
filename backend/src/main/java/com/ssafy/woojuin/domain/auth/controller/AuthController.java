package com.ssafy.woojuin.domain.auth.controller;

import com.ssafy.woojuin.domain.auth.dto.LoginRequest;
import com.ssafy.woojuin.domain.auth.dto.SignupRequest;
import com.ssafy.woojuin.domain.auth.dto.TokenRefreshRequest;
import com.ssafy.woojuin.domain.auth.dto.TokenResponse;
import com.ssafy.woojuin.domain.auth.dto.UserProfileResponse;
import com.ssafy.woojuin.domain.auth.service.LoginService;
import com.ssafy.woojuin.domain.auth.service.LogoutService;
import com.ssafy.woojuin.domain.auth.service.SignupService;
import com.ssafy.woojuin.domain.auth.service.TokenRefreshService;
import com.ssafy.woojuin.global.common.ApiResponse;
import com.ssafy.woojuin.global.security.aop.AuthenticatedUser;
import com.ssafy.woojuin.global.security.aop.CurrentUserResolver;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final SignupService signupService;
    private final LoginService loginService;
    private final TokenRefreshService tokenRefreshService;
    private final LogoutService logoutService;
    private final CurrentUserResolver currentUserResolver;

    public AuthController(SignupService signupService, LoginService loginService,
                           TokenRefreshService tokenRefreshService, LogoutService logoutService,
                           CurrentUserResolver currentUserResolver) {
        this.signupService = signupService;
        this.loginService = loginService;
        this.tokenRefreshService = tokenRefreshService;
        this.logoutService = logoutService;
        this.currentUserResolver = currentUserResolver;
    }

    @PostMapping("/signup")
    public ApiResponse<UserProfileResponse> signup(@Valid @RequestBody SignupRequest request) {
        return ApiResponse.success(UserProfileResponse.from(signupService.signup(request)));
    }

    @PostMapping("/login")
    public ApiResponse<TokenResponse> login(@Valid @RequestBody LoginRequest request) {
        return ApiResponse.success(loginService.login(request));
    }

    @PostMapping("/token/refresh")
    public ApiResponse<TokenResponse> refresh(@Valid @RequestBody TokenRefreshRequest request) {
        return ApiResponse.success(tokenRefreshService.refresh(request.refreshToken()));
    }

    @AuthenticatedUser
    @PostMapping("/logout")
    public ApiResponse<Void> logout() {
        logoutService.logout(currentUserResolver.resolveUserId());
        return ApiResponse.success(null);
    }
}
