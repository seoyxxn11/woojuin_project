package com.ssafy.woojuin.domain.workspace.service;

import com.ssafy.woojuin.domain.workspace.dto.UpdateMemberRoleRequest;
import com.ssafy.woojuin.domain.workspace.dto.WorkspaceMemberResponse;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceMember;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceRole;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceLastOwnerException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceMemberNotFoundException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceMemberRequiredException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceNotFoundException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceOwnerRequiredException;
import com.ssafy.woojuin.domain.workspace.repository.WorkspaceMemberRepository;
import com.ssafy.woojuin.domain.workspace.repository.WorkspaceRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * OWNER가 0명이 되는 상태를 항상 막는다 (마지막 OWNER 강등/제거 금지 — 사용자 확인 완료).
 * 멤버 목록 조회는 OWNER/MEMBER 구분 없이 워크스페이스 멤버라면 누구나 가능하다.
 */
@Service
public class WorkspaceMemberService {

    private final WorkspaceRepository workspaceRepository;
    private final WorkspaceMemberRepository workspaceMemberRepository;

    public WorkspaceMemberService(WorkspaceRepository workspaceRepository,
                                   WorkspaceMemberRepository workspaceMemberRepository) {
        this.workspaceRepository = workspaceRepository;
        this.workspaceMemberRepository = workspaceMemberRepository;
    }

    @Transactional(readOnly = true)
    public List<WorkspaceMemberResponse> list(Long workspaceId, Long requesterId) {
        findWorkspace(workspaceId);
        findMembership(workspaceId, requesterId);

        return workspaceMemberRepository.findByWorkspaceId(workspaceId).stream()
                .map(WorkspaceMemberResponse::of)
                .toList();
    }

    @Transactional
    public WorkspaceMemberResponse updateRole(Long workspaceId, Long targetUserId, Long requesterId,
                                               UpdateMemberRoleRequest request) {
        findWorkspace(workspaceId);
        requireOwner(workspaceId, requesterId);
        WorkspaceMember target = findTargetMembership(workspaceId, targetUserId);

        if (target.getRole() == WorkspaceRole.OWNER && request.role() != WorkspaceRole.OWNER) {
            requireNotLastOwner(workspaceId);
        }

        target.updateRole(request.role());
        return WorkspaceMemberResponse.of(target);
    }

    @Transactional
    public void remove(Long workspaceId, Long targetUserId, Long requesterId) {
        findWorkspace(workspaceId);
        WorkspaceMember target = findTargetMembership(workspaceId, targetUserId);

        if (!requesterId.equals(targetUserId)) {
            requireOwner(workspaceId, requesterId);
        }
        if (target.getRole() == WorkspaceRole.OWNER) {
            requireNotLastOwner(workspaceId);
        }

        workspaceMemberRepository.delete(target);
    }

    private void findWorkspace(Long workspaceId) {
        workspaceRepository.findById(workspaceId)
                .orElseThrow(() -> new WorkspaceNotFoundException(workspaceId));
    }

    private WorkspaceMember findMembership(Long workspaceId, Long userId) {
        return workspaceMemberRepository.findByWorkspaceIdAndUserId(workspaceId, userId)
                .orElseThrow(() -> new WorkspaceMemberRequiredException(workspaceId));
    }

    /** 대상 유저에 대한 조회. 요청자 본인의 멤버십 여부(403)와 달리, 대상이 없으면 404다. */
    private WorkspaceMember findTargetMembership(Long workspaceId, Long userId) {
        return workspaceMemberRepository.findByWorkspaceIdAndUserId(workspaceId, userId)
                .orElseThrow(() -> new WorkspaceMemberNotFoundException(workspaceId, userId));
    }

    private void requireOwner(Long workspaceId, Long userId) {
        WorkspaceMember member = findMembership(workspaceId, userId);
        if (member.getRole() != WorkspaceRole.OWNER) {
            throw new WorkspaceOwnerRequiredException(workspaceId);
        }
    }

    private void requireNotLastOwner(Long workspaceId) {
        if (workspaceMemberRepository.countByWorkspaceIdAndRole(workspaceId, WorkspaceRole.OWNER) <= 1) {
            throw new WorkspaceLastOwnerException(workspaceId);
        }
    }
}
