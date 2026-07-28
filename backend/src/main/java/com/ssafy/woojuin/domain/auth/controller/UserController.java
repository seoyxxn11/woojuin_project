package com.ssafy.woojuin.domain.auth.controller;

import com.ssafy.woojuin.domain.auth.dto.UpdateProfileRequest;
import com.ssafy.woojuin.domain.auth.dto.UserProfileResponse;
import com.ssafy.woojuin.domain.auth.service.UserProfileService;
import com.ssafy.woojuin.global.common.ApiResponse;
import com.ssafy.woojuin.global.security.aop.AuthenticatedUser;
import com.ssafy.woojuin.global.security.aop.CurrentUserResolver;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/users")
public class UserController {

    private final UserProfileService userProfileService;
    private final CurrentUserResolver currentUserResolver;

    public UserController(UserProfileService userProfileService, CurrentUserResolver currentUserResolver) {
        this.userProfileService = userProfileService;
        this.currentUserResolver = currentUserResolver;
    }

    @AuthenticatedUser
    @GetMapping("/me")
    public ApiResponse<UserProfileResponse> getMyProfile() {
        Long userId = currentUserResolver.resolveUserId();
        return ApiResponse.success(userProfileService.getProfile(userId));
    }

    @AuthenticatedUser
    @PatchMapping("/me")
    public ApiResponse<UserProfileResponse> updateMyProfile(@Valid @RequestBody UpdateProfileRequest request) {
        Long userId = currentUserResolver.resolveUserId();
        return ApiResponse.success(userProfileService.updateProfile(userId, request));
    }
}
