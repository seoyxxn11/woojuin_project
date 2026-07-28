package com.ssafy.woojuin.domain.workspace.service;

import com.ssafy.woojuin.domain.auth.entity.AuthProvider;
import com.ssafy.woojuin.domain.auth.entity.User;
import com.ssafy.woojuin.domain.workspace.dto.UpdateMemberRoleRequest;
import com.ssafy.woojuin.domain.workspace.dto.WorkspaceMemberResponse;
import com.ssafy.woojuin.domain.workspace.entity.Workspace;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceMember;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceRole;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceType;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceLastOwnerException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceMemberNotFoundException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceMemberRequiredException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceNotFoundException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceOwnerRequiredException;
import com.ssafy.woojuin.domain.workspace.repository.WorkspaceMemberRepository;
import com.ssafy.woojuin.domain.workspace.repository.WorkspaceRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class WorkspaceMemberServiceTest {

    @Mock
    private WorkspaceRepository workspaceRepository;

    @Mock
    private WorkspaceMemberRepository workspaceMemberRepository;

    @InjectMocks
    private WorkspaceMemberService workspaceMemberService;

    private User user(Long id) {
        User user = User.builder()
                .email("test" + id + "@woojuin.com")
                .provider(AuthProvider.LOCAL)
                .emailVerified(true)
                .nickname("유저" + id)
                .build();
        ReflectionTestUtils.setField(user, "id", id);
        return user;
    }

    private Workspace workspace(Long id, User creator) {
        Workspace workspace = Workspace.builder().name("우리팀").type(WorkspaceType.TEAM).createdBy(creator).build();
        ReflectionTestUtils.setField(workspace, "id", id);
        return workspace;
    }

    private WorkspaceMember member(Workspace ws, User user, WorkspaceRole role) {
        return WorkspaceMember.builder().workspace(ws).user(user).role(role).build();
    }

    @Test
    @DisplayName("멤버면 전체 멤버 목록을 조회할 수 있다")
    void list_member_returnsAllMembers() {
        User owner = user(1L);
        User me = user(2L);
        Workspace ws = workspace(10L, owner);
        WorkspaceMember ownerMembership = member(ws, owner, WorkspaceRole.OWNER);
        WorkspaceMember myMembership = member(ws, me, WorkspaceRole.MEMBER);
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 2L)).thenReturn(Optional.of(myMembership));
        when(workspaceMemberRepository.findByWorkspaceId(10L)).thenReturn(List.of(ownerMembership, myMembership));

        List<WorkspaceMemberResponse> result = workspaceMemberService.list(10L, 2L);

        assertThat(result).hasSize(2);
    }

    @Test
    @DisplayName("멤버가 아니면 목록 조회 시 403 예외를 던진다")
    void list_notMember_throwsMemberRequired() {
        User owner = user(1L);
        Workspace ws = workspace(10L, owner);
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> workspaceMemberService.list(10L, 99L))
                .isInstanceOf(WorkspaceMemberRequiredException.class);
    }

    @Test
    @DisplayName("존재하지 않는 워크스페이스면 목록 조회 시 404 예외를 던진다")
    void list_workspaceNotFound_throwsNotFound() {
        when(workspaceRepository.findById(999L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> workspaceMemberService.list(999L, 1L))
                .isInstanceOf(WorkspaceNotFoundException.class);
    }

    @Test
    @DisplayName("OWNER면 다른 멤버의 역할을 변경할 수 있다")
    void updateRole_owner_updatesTargetRole() {
        User owner = user(1L);
        User target = user(2L);
        Workspace ws = workspace(10L, owner);
        WorkspaceMember ownerMembership = member(ws, owner, WorkspaceRole.OWNER);
        WorkspaceMember targetMembership = member(ws, target, WorkspaceRole.MEMBER);
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 1L)).thenReturn(Optional.of(ownerMembership));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 2L)).thenReturn(Optional.of(targetMembership));

        WorkspaceMemberResponse response =
                workspaceMemberService.updateRole(10L, 2L, 1L, new UpdateMemberRoleRequest(WorkspaceRole.OWNER));

        assertThat(response.role()).isEqualTo(WorkspaceRole.OWNER);
        assertThat(targetMembership.getRole()).isEqualTo(WorkspaceRole.OWNER);
    }

    @Test
    @DisplayName("OWNER가 아니면 역할 변경 시 403 예외를 던진다")
    void updateRole_notOwner_throwsOwnerRequired() {
        User me = user(1L);
        User target = user(2L);
        Workspace ws = workspace(10L, me);
        WorkspaceMember myMembership = member(ws, me, WorkspaceRole.MEMBER);
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 1L)).thenReturn(Optional.of(myMembership));

        assertThatThrownBy(() -> workspaceMemberService.updateRole(
                10L, 2L, 1L, new UpdateMemberRoleRequest(WorkspaceRole.OWNER)))
                .isInstanceOf(WorkspaceOwnerRequiredException.class);
    }

    @Test
    @DisplayName("대상이 멤버가 아니면 역할 변경 시 404 예외를 던진다")
    void updateRole_targetNotMember_throwsMemberNotFound() {
        User owner = user(1L);
        Workspace ws = workspace(10L, owner);
        WorkspaceMember ownerMembership = member(ws, owner, WorkspaceRole.OWNER);
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 1L)).thenReturn(Optional.of(ownerMembership));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 999L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> workspaceMemberService.updateRole(
                10L, 999L, 1L, new UpdateMemberRoleRequest(WorkspaceRole.MEMBER)))
                .isInstanceOf(WorkspaceMemberNotFoundException.class);
    }

    @Test
    @DisplayName("마지막 OWNER를 MEMBER로 강등하려 하면 예외를 던진다")
    void updateRole_demotingLastOwner_throwsLastOwner() {
        User owner = user(1L);
        Workspace ws = workspace(10L, owner);
        WorkspaceMember ownerMembership = member(ws, owner, WorkspaceRole.OWNER);
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 1L)).thenReturn(Optional.of(ownerMembership));
        when(workspaceMemberRepository.countByWorkspaceIdAndRole(10L, WorkspaceRole.OWNER)).thenReturn(1L);

        assertThatThrownBy(() -> workspaceMemberService.updateRole(
                10L, 1L, 1L, new UpdateMemberRoleRequest(WorkspaceRole.MEMBER)))
                .isInstanceOf(WorkspaceLastOwnerException.class);
    }

    @Test
    @DisplayName("OWNER는 다른 멤버를 제거할 수 있다")
    void remove_ownerRemovesOther_removesTarget() {
        User owner = user(1L);
        User target = user(2L);
        Workspace ws = workspace(10L, owner);
        WorkspaceMember ownerMembership = member(ws, owner, WorkspaceRole.OWNER);
        WorkspaceMember targetMembership = member(ws, target, WorkspaceRole.MEMBER);
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 2L)).thenReturn(Optional.of(targetMembership));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 1L)).thenReturn(Optional.of(ownerMembership));

        workspaceMemberService.remove(10L, 2L, 1L);

        verify(workspaceMemberRepository).delete(targetMembership);
    }

    @Test
    @DisplayName("본인은 스스로 탈퇴할 수 있다")
    void remove_selfLeave_removesSelf() {
        User owner = user(1L);
        User me = user(2L);
        Workspace ws = workspace(10L, owner);
        WorkspaceMember myMembership = member(ws, me, WorkspaceRole.MEMBER);
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 2L)).thenReturn(Optional.of(myMembership));

        workspaceMemberService.remove(10L, 2L, 2L);

        verify(workspaceMemberRepository).delete(myMembership);
    }

    @Test
    @DisplayName("OWNER가 아니면 다른 사람을 제거할 수 없다")
    void remove_nonOwnerRemovingOther_throwsOwnerRequired() {
        User me = user(1L);
        User target = user(2L);
        Workspace ws = workspace(10L, me);
        WorkspaceMember myMembership = member(ws, me, WorkspaceRole.MEMBER);
        WorkspaceMember targetMembership = member(ws, target, WorkspaceRole.MEMBER);
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 2L)).thenReturn(Optional.of(targetMembership));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 1L)).thenReturn(Optional.of(myMembership));

        assertThatThrownBy(() -> workspaceMemberService.remove(10L, 2L, 1L))
                .isInstanceOf(WorkspaceOwnerRequiredException.class);

        verify(workspaceMemberRepository, never()).delete(targetMembership);
    }

    @Test
    @DisplayName("마지막 OWNER는 스스로도 탈퇴할 수 없다")
    void remove_removingLastOwner_throwsLastOwner() {
        User owner = user(1L);
        Workspace ws = workspace(10L, owner);
        WorkspaceMember ownerMembership = member(ws, owner, WorkspaceRole.OWNER);
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 1L)).thenReturn(Optional.of(ownerMembership));
        when(workspaceMemberRepository.countByWorkspaceIdAndRole(10L, WorkspaceRole.OWNER)).thenReturn(1L);

        assertThatThrownBy(() -> workspaceMemberService.remove(10L, 1L, 1L))
                .isInstanceOf(WorkspaceLastOwnerException.class);

        verify(workspaceMemberRepository, never()).delete(ownerMembership);
    }

    @Test
    @DisplayName("대상이 멤버가 아니면 제거 시 404 예외를 던진다")
    void remove_targetNotMember_throwsMemberNotFound() {
        User owner = user(1L);
        Workspace ws = workspace(10L, owner);
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 999L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> workspaceMemberService.remove(10L, 999L, 1L))
                .isInstanceOf(WorkspaceMemberNotFoundException.class);
    }
}
