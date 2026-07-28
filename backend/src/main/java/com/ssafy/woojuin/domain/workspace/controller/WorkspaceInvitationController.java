package com.ssafy.woojuin.domain.workspace.controller;

import com.ssafy.woojuin.domain.workspace.dto.WorkspaceInvitationResponse;
import com.ssafy.woojuin.domain.workspace.service.WorkspaceInvitationService;
import com.ssafy.woojuin.global.common.ApiResponse;
import com.ssafy.woojuin.global.security.aop.AuthenticatedUser;
import com.ssafy.woojuin.global.security.aop.CurrentUserResolver;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** 워크스페이스 소속 하위 리소스로서의 초대(생성). 코드 단위 조회/수락은 InvitationController 참고. */
@RestController
@RequestMapping("/api/workspaces/{workspaceId}/invitations")
public class WorkspaceInvitationController {

    private final WorkspaceInvitationService workspaceInvitationService;
    private final CurrentUserResolver currentUserResolver;

    public WorkspaceInvitationController(WorkspaceInvitationService workspaceInvitationService,
                                          CurrentUserResolver currentUserResolver) {
        this.workspaceInvitationService = workspaceInvitationService;
        this.currentUserResolver = currentUserResolver;
    }

    @AuthenticatedUser
    @PostMapping
    public ResponseEntity<ApiResponse<WorkspaceInvitationResponse>> create(@PathVariable Long workspaceId) {
        Long userId = currentUserResolver.resolveUserId();
        WorkspaceInvitationResponse response = workspaceInvitationService.createInvitation(workspaceId, userId);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.of(201, "success", response));
    }
}
