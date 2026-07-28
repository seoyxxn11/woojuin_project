package com.ssafy.woojuin.domain.workspace.service;

import com.ssafy.woojuin.domain.auth.entity.User;
import com.ssafy.woojuin.domain.auth.event.UserSignedUpEvent;
import com.ssafy.woojuin.domain.auth.repository.UserRepository;
import com.ssafy.woojuin.domain.workspace.dto.WorkspaceCreateRequest;
import com.ssafy.woojuin.domain.workspace.dto.WorkspaceResponse;
import com.ssafy.woojuin.domain.workspace.dto.WorkspaceUpdateRequest;
import com.ssafy.woojuin.domain.workspace.entity.Workspace;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceMember;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceRole;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceType;
import com.ssafy.woojuin.domain.workspace.event.WorkspaceCreatedEvent;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceMemberRequiredException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceNotFoundException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceOwnerRequiredException;
import com.ssafy.woojuin.domain.workspace.repository.WorkspaceInvitationRepository;
import com.ssafy.woojuin.domain.workspace.repository.WorkspaceMemberRepository;
import com.ssafy.woojuin.domain.workspace.repository.WorkspaceRepository;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * 삭제 시 workspace_members / workspace_invitations는 함께 정리하지만,
 * items 등 다른 도메인 데이터는 여기서 건드리지 않는다 (도메인 경계 밖).
 * ERD 설계 노트의 "하위 items CASCADE"는 아직 미해결 — 후속 조율 필요.
 */
@Service
public class WorkspaceService {

    private final WorkspaceRepository workspaceRepository;
    private final WorkspaceMemberRepository workspaceMemberRepository;
    private final WorkspaceInvitationRepository workspaceInvitationRepository;
    private final UserRepository userRepository;
    private final ApplicationEventPublisher eventPublisher;

    public WorkspaceService(WorkspaceRepository workspaceRepository, WorkspaceMemberRepository workspaceMemberRepository,
                             WorkspaceInvitationRepository workspaceInvitationRepository, UserRepository userRepository,
                             ApplicationEventPublisher eventPublisher) {
        this.workspaceRepository = workspaceRepository;
        this.workspaceMemberRepository = workspaceMemberRepository;
        this.workspaceInvitationRepository = workspaceInvitationRepository;
        this.userRepository = userRepository;
        this.eventPublisher = eventPublisher;
    }

    @Transactional
    public WorkspaceResponse create(Long userId, WorkspaceCreateRequest request) {
        User creator = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다"));

        Workspace workspace = workspaceRepository.save(
                Workspace.builder().name(request.name()).type(request.type()).createdBy(creator).build());
        workspaceMemberRepository.save(
                WorkspaceMember.builder().workspace(workspace).user(creator).role(WorkspaceRole.OWNER).build());

        // 기본 카테고리 시드 등 후속 처리는 이벤트로 위임한다(이 서비스는 카테고리 도메인을 모른다).
        // 동기 리스너라 같은 트랜잭션에서 처리돼, 시드 실패 시 워크스페이스 생성도 롤백된다.
        eventPublisher.publishEvent(new WorkspaceCreatedEvent(workspace.getId()));

        return WorkspaceResponse.of(workspace, WorkspaceRole.OWNER);
    }

    @Transactional(readOnly = true)
    public List<WorkspaceResponse> list(Long userId) {
        return workspaceMemberRepository.findByUserId(userId).stream()
                .map(member -> WorkspaceResponse.of(member.getWorkspace(), member.getRole()))
                .toList();
    }

    @Transactional(readOnly = true)
    public WorkspaceResponse get(Long workspaceId, Long userId) {
        Workspace workspace = findWorkspace(workspaceId);
        WorkspaceMember member = findMembership(workspaceId, userId);
        return WorkspaceResponse.of(workspace, member.getRole());
    }

    @Transactional
    public WorkspaceResponse update(Long workspaceId, Long userId, WorkspaceUpdateRequest request) {
        Workspace workspace = findWorkspace(workspaceId);
        WorkspaceMember member = requireOwner(workspaceId, userId);

        workspace.updateName(request.name());
        return WorkspaceResponse.of(workspace, member.getRole());
    }

    @Transactional
    public void delete(Long workspaceId, Long userId) {
        Workspace workspace = findWorkspace(workspaceId);
        requireOwner(workspaceId, userId);

        workspaceMemberRepository.deleteAll(workspaceMemberRepository.findByWorkspaceId(workspaceId));
        workspaceInvitationRepository.deleteAll(workspaceInvitationRepository.findByWorkspaceId(workspaceId));
        workspaceRepository.delete(workspace);
    }

    /** 회원가입 이벤트에 반응해 PERSONAL 워크스페이스 생성을 시도한다. */
    @EventListener
    public void onUserSignedUp(UserSignedUpEvent event) {
        ensurePersonalWorkspace(event.userId());
    }

    /**
     * 이 유저가 PERSONAL 워크스페이스를 갖고 있지 않으면 만들어주고, 있으면 아무것도 하지 않는다(멱등).
     * 회원가입 이벤트뿐 아니라 기존 가입자 백필(PersonalWorkspaceBackfillRunner)에서도 재사용한다.
     */
    @Transactional
    public void ensurePersonalWorkspace(Long userId) {
        boolean alreadyHasPersonalWorkspace = workspaceMemberRepository.findByUserId(userId).stream()
                .anyMatch(member -> member.getWorkspace().getType() == WorkspaceType.PERSONAL);
        if (alreadyHasPersonalWorkspace) {
            return;
        }

        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다"));

        Workspace workspace = workspaceRepository.save(
                Workspace.builder().name("My Space").type(WorkspaceType.PERSONAL).createdBy(user).build());
        workspaceMemberRepository.save(
                WorkspaceMember.builder().workspace(workspace).user(user).role(WorkspaceRole.OWNER).build());
        user.assignPersonalWorkspace(workspace.getId());

        eventPublisher.publishEvent(new WorkspaceCreatedEvent(workspace.getId()));
    }

    private Workspace findWorkspace(Long workspaceId) {
        return workspaceRepository.findById(workspaceId)
                .orElseThrow(() -> new WorkspaceNotFoundException(workspaceId));
    }

    private WorkspaceMember findMembership(Long workspaceId, Long userId) {
        return workspaceMemberRepository.findByWorkspaceIdAndUserId(workspaceId, userId)
                .orElseThrow(() -> new WorkspaceMemberRequiredException(workspaceId));
    }

    private WorkspaceMember requireOwner(Long workspaceId, Long userId) {
        WorkspaceMember member = findMembership(workspaceId, userId);
        if (member.getRole() != WorkspaceRole.OWNER) {
            throw new WorkspaceOwnerRequiredException(workspaceId);
        }
        return member;
    }
}
