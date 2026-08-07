package com.ssafy.woojuin.domain.auth.controller;

import com.ssafy.woojuin.domain.auth.dto.DeviceLinkApproveRequest;
import com.ssafy.woojuin.domain.auth.dto.DeviceLinkPollRequest;
import com.ssafy.woojuin.domain.auth.dto.DeviceLinkPollResponse;
import com.ssafy.woojuin.domain.auth.dto.DeviceLinkStartResponse;
import com.ssafy.woojuin.domain.auth.service.DeviceLinkService;
import com.ssafy.woojuin.global.common.ApiResponse;
import com.ssafy.woojuin.global.security.aop.AuthenticatedUser;
import com.ssafy.woojuin.global.security.aop.CurrentUserResolver;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 워치 링크 코드 로그인 (S15P11C105-458).
 *
 * start·poll 은 비인증이다 — 아직 토큰이 없는 기기가 부르는 경로라서 그렇다.
 * approve 만 인증을 요구한다: 코드에 계정을 붙이는 쪽이 웹의 로그인된 사용자다.
 */
@RestController
@RequestMapping("/api/auth/device-link")
public class DeviceLinkController {

    private final DeviceLinkService deviceLinkService;
    private final CurrentUserResolver currentUserResolver;

    public DeviceLinkController(DeviceLinkService deviceLinkService,
                                CurrentUserResolver currentUserResolver) {
        this.deviceLinkService = deviceLinkService;
        this.currentUserResolver = currentUserResolver;
    }

    /** 워치: 화면에 띄울 코드 발급 */
    @PostMapping
    public ApiResponse<DeviceLinkStartResponse> start() {
        return ApiResponse.success(deviceLinkService.start());
    }

    /** 웹(기기 관리 화면): 워치 화면의 코드를 입력해 승인 */
    @AuthenticatedUser
    @PostMapping("/approve")
    public ApiResponse<Void> approve(@Valid @RequestBody DeviceLinkApproveRequest request) {
        deviceLinkService.approve(currentUserResolver.resolveUserId(), request.code());
        return ApiResponse.success(null);
    }

    /**
     * 기기: 승인 여부 폴링. 승인되면 토큰이 실려 온다 — UA(또는 본문의 client 표식)가
     * 기기 목록의 이름이 된다. client 가 필요한 이유는 DeviceLinkPollRequest 참고.
     */
    @PostMapping("/poll")
    public ApiResponse<DeviceLinkPollResponse> poll(
            @Valid @RequestBody DeviceLinkPollRequest request,
            @RequestHeader(value = "User-Agent", required = false) String userAgent) {
        return ApiResponse.success(deviceLinkService.poll(request.code(), userAgent, request.client()));
    }
}
