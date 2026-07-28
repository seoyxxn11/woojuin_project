package com.ssafy.woojuin.domain.workspace.service;

import com.ssafy.woojuin.domain.auth.entity.AuthProvider;
import com.ssafy.woojuin.domain.auth.entity.User;
import com.ssafy.woojuin.domain.auth.event.UserSignedUpEvent;
import com.ssafy.woojuin.domain.auth.repository.UserRepository;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceMemberRequiredException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceNotFoundException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceOwnerRequiredException;
import com.ssafy.woojuin.domain.workspace.dto.WorkspaceCreateRequest;
import com.ssafy.woojuin.domain.workspace.dto.WorkspaceResponse;
import com.ssafy.woojuin.domain.workspace.dto.WorkspaceUpdateRequest;
import com.ssafy.woojuin.domain.workspace.entity.Workspace;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceMember;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceRole;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceType;
import com.ssafy.woojuin.domain.workspace.repository.WorkspaceInvitationRepository;
import com.ssafy.woojuin.domain.workspace.repository.WorkspaceMemberRepository;
import com.ssafy.woojuin.domain.workspace.repository.WorkspaceRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class WorkspaceServiceTest {

    @Mock
    private WorkspaceRepository workspaceRepository;

    @Mock
    private WorkspaceMemberRepository workspaceMemberRepository;

    @Mock
    private WorkspaceInvitationRepository workspaceInvitationRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private org.springframework.context.ApplicationEventPublisher eventPublisher;

    @InjectMocks
    private WorkspaceService workspaceService;

    private User user(Long id) {
        User user = User.builder()
                .email("test@woojuin.com")
                .provider(AuthProvider.LOCAL)
                .emailVerified(true)
                .nickname("우주인")
                .build();
        ReflectionTestUtils.setField(user, "id", id);
        return user;
    }

    private Workspace workspace(Long id, User creator) {
        Workspace workspace = Workspace.builder().name("우리팀").type(WorkspaceType.TEAM).createdBy(creator).build();
        ReflectionTestUtils.setField(workspace, "id", id);
        return workspace;
    }

    @Test
    @DisplayName("생성하면 워크스페이스를 저장하고 생성자를 OWNER로 등록한다")
    void create_savesWorkspaceAndAddsCreatorAsOwner() {
        User creator = user(1L);
        when(userRepository.findById(1L)).thenReturn(Optional.of(creator));
        when(workspaceRepository.save(any(Workspace.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(workspaceMemberRepository.save(any(WorkspaceMember.class))).thenAnswer(invocation -> invocation.getArgument(0));

        WorkspaceResponse response = workspaceService.create(1L, new WorkspaceCreateRequest("우리팀", WorkspaceType.TEAM));

        assertThat(response.name()).isEqualTo("우리팀");
        assertThat(response.type()).isEqualTo(WorkspaceType.TEAM);
        assertThat(response.role()).isEqualTo(WorkspaceRole.OWNER);

        ArgumentCaptor<WorkspaceMember> captor = ArgumentCaptor.forClass(WorkspaceMember.class);
        verify(workspaceMemberRepository).save(captor.capture());
        assertThat(captor.getValue().getRole()).isEqualTo(WorkspaceRole.OWNER);
        assertThat(captor.getValue().getUser()).isEqualTo(creator);
    }

    @Test
    @DisplayName("내가 속한 워크스페이스 목록을 반환한다")
    void list_returnsWorkspacesForUser() {
        User me = user(1L);
        Workspace ws = workspace(10L, me);
        WorkspaceMember membership = WorkspaceMember.builder().workspace(ws).user(me).role(WorkspaceRole.MEMBER).build();
        when(workspaceMemberRepository.findByUserId(1L)).thenReturn(List.of(membership));

        List<WorkspaceResponse> result = workspaceService.list(1L);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).id()).isEqualTo(10L);
        assertThat(result.get(0).role()).isEqualTo(WorkspaceRole.MEMBER);
    }

    @Test
    @DisplayName("멤버면 워크스페이스 상세를 조회할 수 있다")
    void get_member_returnsWorkspaceResponse() {
        User me = user(1L);
        Workspace ws = workspace(10L, me);
        WorkspaceMember membership = WorkspaceMember.builder().workspace(ws).user(me).role(WorkspaceRole.OWNER).build();
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 1L)).thenReturn(Optional.of(membership));

        WorkspaceResponse response = workspaceService.get(10L, 1L);

        assertThat(response.id()).isEqualTo(10L);
        assertThat(response.role()).isEqualTo(WorkspaceRole.OWNER);
    }

    @Test
    @DisplayName("존재하지 않는 워크스페이스를 조회하면 404 예외를 던진다")
    void get_nonExistentWorkspace_throwsNotFound() {
        when(workspaceRepository.findById(999L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> workspaceService.get(999L, 1L))
                .isInstanceOf(WorkspaceNotFoundException.class);
    }

    @Test
    @DisplayName("멤버가 아니면 조회 시 403 예외를 던진다")
    void get_notMember_throwsMemberRequired() {
        User me = user(1L);
        Workspace ws = workspace(10L, me);
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 1L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> workspaceService.get(10L, 1L))
                .isInstanceOf(WorkspaceMemberRequiredException.class);
    }

    @Test
    @DisplayName("OWNER면 이름을 수정할 수 있다")
    void update_owner_updatesNameAndReturnsResponse() {
        User me = user(1L);
        Workspace ws = workspace(10L, me);
        WorkspaceMember membership = WorkspaceMember.builder().workspace(ws).user(me).role(WorkspaceRole.OWNER).build();
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 1L)).thenReturn(Optional.of(membership));

        WorkspaceResponse response = workspaceService.update(10L, 1L, new WorkspaceUpdateRequest("새이름"));

        assertThat(response.name()).isEqualTo("새이름");
        assertThat(ws.getName()).isEqualTo("새이름");
    }

    @Test
    @DisplayName("OWNER가 아니면 수정 시 403 예외를 던진다")
    void update_notOwner_throwsOwnerRequired() {
        User me = user(1L);
        Workspace ws = workspace(10L, me);
        WorkspaceMember membership = WorkspaceMember.builder().workspace(ws).user(me).role(WorkspaceRole.MEMBER).build();
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 1L)).thenReturn(Optional.of(membership));

        assertThatThrownBy(() -> workspaceService.update(10L, 1L, new WorkspaceUpdateRequest("새이름")))
                .isInstanceOf(WorkspaceOwnerRequiredException.class);
    }

    @Test
    @DisplayName("OWNER면 삭제 시 워크스페이스와 멤버·초대를 함께 지운다")
    void delete_owner_deletesWorkspaceAndRelatedRows() {
        User me = user(1L);
        Workspace ws = workspace(10L, me);
        WorkspaceMember membership = WorkspaceMember.builder().workspace(ws).user(me).role(WorkspaceRole.OWNER).build();
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 1L)).thenReturn(Optional.of(membership));
        when(workspaceMemberRepository.findByWorkspaceId(10L)).thenReturn(List.of(membership));
        when(workspaceInvitationRepository.findByWorkspaceId(10L)).thenReturn(List.of());

        workspaceService.delete(10L, 1L);

        verify(workspaceMemberRepository).deleteAll(List.of(membership));
        verify(workspaceInvitationRepository).deleteAll(List.of());
        verify(workspaceRepository).delete(ws);
    }

    @Test
    @DisplayName("OWNER가 아니면 삭제 시 403 예외를 던지고 아무것도 지우지 않는다")
    void delete_notOwner_throwsOwnerRequiredAndDeletesNothing() {
        User me = user(1L);
        Workspace ws = workspace(10L, me);
        WorkspaceMember membership = WorkspaceMember.builder().workspace(ws).user(me).role(WorkspaceRole.MEMBER).build();
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 1L)).thenReturn(Optional.of(membership));

        assertThatThrownBy(() -> workspaceService.delete(10L, 1L))
                .isInstanceOf(WorkspaceOwnerRequiredException.class);

        verify(workspaceRepository, never()).delete(any(Workspace.class));
    }

    @Test
    @DisplayName("PERSONAL 워크스페이스가 없으면 생성하고 OWNER로 등록하며 유저에 id를 기록한다")
    void ensurePersonalWorkspace_noPersonalWorkspace_createsAndAssignsToUser() {
        User me = user(1L);
        when(workspaceMemberRepository.findByUserId(1L)).thenReturn(List.of());
        when(userRepository.findById(1L)).thenReturn(Optional.of(me));
        when(workspaceRepository.save(any(Workspace.class))).thenAnswer(invocation -> {
            Workspace ws = invocation.getArgument(0);
            ReflectionTestUtils.setField(ws, "id", 20L);
            return ws;
        });
        when(workspaceMemberRepository.save(any(WorkspaceMember.class))).thenAnswer(invocation -> invocation.getArgument(0));

        workspaceService.ensurePersonalWorkspace(1L);

        ArgumentCaptor<Workspace> workspaceCaptor = ArgumentCaptor.forClass(Workspace.class);
        verify(workspaceRepository).save(workspaceCaptor.capture());
        assertThat(workspaceCaptor.getValue().getType()).isEqualTo(WorkspaceType.PERSONAL);

        ArgumentCaptor<WorkspaceMember> memberCaptor = ArgumentCaptor.forClass(WorkspaceMember.class);
        verify(workspaceMemberRepository).save(memberCaptor.capture());
        assertThat(memberCaptor.getValue().getRole()).isEqualTo(WorkspaceRole.OWNER);
        assertThat(memberCaptor.getValue().getUser()).isEqualTo(me);

        assertThat(me.getPersonalWorkspaceId()).isEqualTo(20L);
    }

    @Test
    @DisplayName("이미 PERSONAL 워크스페이스가 있으면 아무것도 하지 않는다")
    void ensurePersonalWorkspace_alreadyHasPersonalWorkspace_doesNothing() {
        User me = user(1L);
        Workspace personal = Workspace.builder().name("My Space").type(WorkspaceType.PERSONAL).createdBy(me).build();
        WorkspaceMember membership = WorkspaceMember.builder().workspace(personal).user(me).role(WorkspaceRole.OWNER).build();
        when(workspaceMemberRepository.findByUserId(1L)).thenReturn(List.of(membership));

        workspaceService.ensurePersonalWorkspace(1L);

        verify(workspaceRepository, never()).save(any(Workspace.class));
        verify(workspaceMemberRepository, never()).save(any(WorkspaceMember.class));
    }

    @Test
    @DisplayName("UserSignedUpEvent를 받으면 개인 워크스페이스 생성을 시도한다")
    void onUserSignedUp_receivesEvent_ensuresPersonalWorkspace() {
        User me = user(1L);
        when(workspaceMemberRepository.findByUserId(1L)).thenReturn(List.of());
        when(userRepository.findById(1L)).thenReturn(Optional.of(me));
        when(workspaceRepository.save(any(Workspace.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(workspaceMemberRepository.save(any(WorkspaceMember.class))).thenAnswer(invocation -> invocation.getArgument(0));

        workspaceService.onUserSignedUp(new UserSignedUpEvent(1L));

        verify(workspaceRepository).save(any(Workspace.class));
    }
}
