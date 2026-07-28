package com.ssafy.woojuin.domain.workspace.controller;

import com.ssafy.woojuin.domain.workspace.dto.UpdateMemberRoleRequest;
import com.ssafy.woojuin.domain.workspace.dto.WorkspaceMemberResponse;
import com.ssafy.woojuin.domain.workspace.service.WorkspaceMemberService;
import com.ssafy.woojuin.global.common.ApiResponse;
import com.ssafy.woojuin.global.security.aop.AuthenticatedUser;
import com.ssafy.woojuin.global.security.aop.CurrentUserResolver;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/workspaces/{workspaceId}/members")
public class WorkspaceMemberController {

    private final WorkspaceMemberService workspaceMemberService;
    private final CurrentUserResolver currentUserResolver;

    public WorkspaceMemberController(WorkspaceMemberService workspaceMemberService,
                                      CurrentUserResolver currentUserResolver) {
        this.workspaceMemberService = workspaceMemberService;
        this.currentUserResolver = currentUserResolver;
    }

    @AuthenticatedUser
    @GetMapping
    public ResponseEntity<ApiResponse<List<WorkspaceMemberResponse>>> list(@PathVariable Long workspaceId) {
        Long requesterId = currentUserResolver.resolveUserId();
        return ResponseEntity.ok(ApiResponse.success(workspaceMemberService.list(workspaceId, requesterId)));
    }

    @AuthenticatedUser
    @PatchMapping("/{userId}")
    public ResponseEntity<ApiResponse<WorkspaceMemberResponse>> updateRole(
            @PathVariable Long workspaceId, @PathVariable("userId") Long targetUserId,
            @RequestBody UpdateMemberRoleRequest request) {
        Long requesterId = currentUserResolver.resolveUserId();
        return ResponseEntity.ok(ApiResponse.success(
                workspaceMemberService.updateRole(workspaceId, targetUserId, requesterId, request)));
    }

    /** 자기 자신의 userId로 호출하면 탈퇴, 다른 사람의 userId면 OWNER의 강퇴. */
    @AuthenticatedUser
    @DeleteMapping("/{userId}")
    public ResponseEntity<ApiResponse<Void>> remove(
            @PathVariable Long workspaceId, @PathVariable("userId") Long targetUserId) {
        Long requesterId = currentUserResolver.resolveUserId();
        workspaceMemberService.remove(workspaceId, targetUserId, requesterId);
        return ResponseEntity.ok(ApiResponse.success(null));
    }
}
