package com.ssafy.woojuin.domain.workspace.controller;

import com.ssafy.woojuin.domain.workspace.dto.WorkspaceCreateRequest;
import com.ssafy.woojuin.domain.workspace.dto.WorkspaceResponse;
import com.ssafy.woojuin.domain.workspace.dto.WorkspaceUpdateRequest;
import com.ssafy.woojuin.domain.workspace.service.WorkspaceService;
import com.ssafy.woojuin.global.common.ApiResponse;
import com.ssafy.woojuin.global.security.aop.AuthenticatedUser;
import com.ssafy.woojuin.global.security.aop.CurrentUserResolver;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/workspaces")
public class WorkspaceController {

    private final WorkspaceService workspaceService;
    private final CurrentUserResolver currentUserResolver;

    public WorkspaceController(WorkspaceService workspaceService, CurrentUserResolver currentUserResolver) {
        this.workspaceService = workspaceService;
        this.currentUserResolver = currentUserResolver;
    }

    @AuthenticatedUser
    @PostMapping
    public ResponseEntity<ApiResponse<WorkspaceResponse>> create(@RequestBody WorkspaceCreateRequest request) {
        Long userId = currentUserResolver.resolveUserId();
        WorkspaceResponse response = workspaceService.create(userId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.of(201, "success", response));
    }

    @AuthenticatedUser
    @GetMapping
    public ResponseEntity<ApiResponse<List<WorkspaceResponse>>> list() {
        Long userId = currentUserResolver.resolveUserId();
        return ResponseEntity.ok(ApiResponse.success(workspaceService.list(userId)));
    }

    @AuthenticatedUser
    @GetMapping("/{workspaceId}")
    public ResponseEntity<ApiResponse<WorkspaceResponse>> get(@PathVariable Long workspaceId) {
        Long userId = currentUserResolver.resolveUserId();
        return ResponseEntity.ok(ApiResponse.success(workspaceService.get(workspaceId, userId)));
    }

    @AuthenticatedUser
    @PatchMapping("/{workspaceId}")
    public ResponseEntity<ApiResponse<WorkspaceResponse>> update(
            @PathVariable Long workspaceId, @RequestBody WorkspaceUpdateRequest request) {
        Long userId = currentUserResolver.resolveUserId();
        return ResponseEntity.ok(ApiResponse.success(workspaceService.update(workspaceId, userId, request)));
    }

    @AuthenticatedUser
    @DeleteMapping("/{workspaceId}")
    public ResponseEntity<ApiResponse<Void>> delete(@PathVariable Long workspaceId) {
        Long userId = currentUserResolver.resolveUserId();
        workspaceService.delete(workspaceId, userId);
        return ResponseEntity.ok(ApiResponse.success(null));
    }
}
