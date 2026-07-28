package com.ssafy.woojuin.domain.workspace.service;

import com.ssafy.woojuin.domain.auth.entity.User;
import com.ssafy.woojuin.domain.auth.repository.UserRepository;
import com.ssafy.woojuin.domain.workspace.dto.WorkspaceInvitationResponse;
import com.ssafy.woojuin.domain.workspace.dto.WorkspaceResponse;
import com.ssafy.woojuin.domain.workspace.entity.Workspace;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceInvitation;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceMember;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceRole;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceType;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceInvitationExpiredException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceInvitationNotAllowedException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceInvitationNotFoundException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceMemberRequiredException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceNotFoundException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceOwnerRequiredException;
import com.ssafy.woojuin.domain.workspace.repository.WorkspaceInvitationRepository;
import com.ssafy.woojuin.domain.workspace.repository.WorkspaceMemberRepository;
import com.ssafy.woojuin.domain.workspace.repository.WorkspaceRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * 초대 코드는 사용 여부를 별도로 추적하지 않는다 (ERD에 그런 컬럼이 없음) — 만료 전까지는
 * 링크 하나로 여러 명이 가입할 수 있는 재사용형 링크로 취급한다.
 * 유효기간은 명세에 정해진 값이 없어 7일로 둔다.
 */
@Service
public class WorkspaceInvitationService {

    private static final Duration INVITATION_VALIDITY = Duration.ofDays(7);

    private final WorkspaceRepository workspaceRepository;
    private final WorkspaceMemberRepository workspaceMemberRepository;
    private final WorkspaceInvitationRepository workspaceInvitationRepository;
    private final UserRepository userRepository;

    public WorkspaceInvitationService(WorkspaceRepository workspaceRepository,
                                       WorkspaceMemberRepository workspaceMemberRepository,
                                       WorkspaceInvitationRepository workspaceInvitationRepository,
                                       UserRepository userRepository) {
        this.workspaceRepository = workspaceRepository;
        this.workspaceMemberRepository = workspaceMemberRepository;
        this.workspaceInvitationRepository = workspaceInvitationRepository;
        this.userRepository = userRepository;
    }

    @Transactional
    public WorkspaceInvitationResponse createInvitation(Long workspaceId, Long userId) {
        Workspace workspace = findWorkspace(workspaceId);
        requireOwner(workspaceId, userId);
        if (workspace.getType() == WorkspaceType.PERSONAL) {
            throw new WorkspaceInvitationNotAllowedException(workspaceId);
        }
        User creator = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다"));

        WorkspaceInvitation invitation = workspaceInvitationRepository.save(WorkspaceInvitation.builder()
                .workspace(workspace)
                .code(UUID.randomUUID().toString())
                .expiresAt(OffsetDateTime.now().plus(INVITATION_VALIDITY))
                .createdBy(creator)
                .build());

        return WorkspaceInvitationResponse.of(invitation);
    }

    @Transactional(readOnly = true)
    public WorkspaceInvitationResponse getInvitation(String code) {
        return WorkspaceInvitationResponse.of(findValidInvitation(code));
    }

    @Transactional
    public WorkspaceResponse accept(String code, Long userId) {
        WorkspaceInvitation invitation = findValidInvitation(code);
        Workspace workspace = invitation.getWorkspace();

        if (workspaceMemberRepository.findByWorkspaceIdAndUserId(workspace.getId(), userId).isPresent()) {
            throw new IllegalArgumentException("이미 가입된 워크스페이스입니다");
        }

        User joiner = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다"));
        workspaceMemberRepository.save(
                WorkspaceMember.builder().workspace(workspace).user(joiner).role(WorkspaceRole.MEMBER).build());

        return WorkspaceResponse.of(workspace, WorkspaceRole.MEMBER);
    }

    private Workspace findWorkspace(Long workspaceId) {
        return workspaceRepository.findById(workspaceId)
                .orElseThrow(() -> new WorkspaceNotFoundException(workspaceId));
    }

    private void requireOwner(Long workspaceId, Long userId) {
        WorkspaceMember member = workspaceMemberRepository.findByWorkspaceIdAndUserId(workspaceId, userId)
                .orElseThrow(() -> new WorkspaceMemberRequiredException(workspaceId));
        if (member.getRole() != WorkspaceRole.OWNER) {
            throw new WorkspaceOwnerRequiredException(workspaceId);
        }
    }

    private WorkspaceInvitation findValidInvitation(String code) {
        WorkspaceInvitation invitation = workspaceInvitationRepository.findByCode(code)
                .orElseThrow(() -> new WorkspaceInvitationNotFoundException(code));
        if (invitation.getExpiresAt().isBefore(OffsetDateTime.now())) {
            throw new WorkspaceInvitationExpiredException(code);
        }
        return invitation;
    }
}
