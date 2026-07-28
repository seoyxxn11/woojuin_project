package com.ssafy.woojuin.domain.workspace.controller;

import com.ssafy.woojuin.domain.workspace.dto.WorkspaceInvitationResponse;
import com.ssafy.woojuin.domain.workspace.dto.WorkspaceResponse;
import com.ssafy.woojuin.domain.workspace.service.WorkspaceInvitationService;
import com.ssafy.woojuin.global.common.ApiResponse;
import com.ssafy.woojuin.global.security.aop.AuthenticatedUser;
import com.ssafy.woojuin.global.security.aop.CurrentUserResolver;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** 초대 코드 단위 조회/수락. 생성은 WorkspaceInvitationController 참고. */
@RestController
@RequestMapping("/api/invitations/{code}")
public class InvitationController {

    private final WorkspaceInvitationService workspaceInvitationService;
    private final CurrentUserResolver currentUserResolver;

    public InvitationController(WorkspaceInvitationService workspaceInvitationService,
                                 CurrentUserResolver currentUserResolver) {
        this.workspaceInvitationService = workspaceInvitationService;
        this.currentUserResolver = currentUserResolver;
    }

    /** 로그인 전에도 초대 내용을 미리 볼 수 있어야 해서 인증을 요구하지 않는다. */
    @GetMapping
    public ResponseEntity<ApiResponse<WorkspaceInvitationResponse>> get(@PathVariable String code) {
        return ResponseEntity.ok(ApiResponse.success(workspaceInvitationService.getInvitation(code)));
    }

    @AuthenticatedUser
    @PostMapping("/accept")
    public ResponseEntity<ApiResponse<WorkspaceResponse>> accept(@PathVariable String code) {
        Long userId = currentUserResolver.resolveUserId();
        return ResponseEntity.ok(ApiResponse.success(workspaceInvitationService.accept(code, userId)));
    }
}
