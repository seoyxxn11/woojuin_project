package com.ssafy.woojuin.domain.workspace.service;

import com.ssafy.woojuin.domain.auth.entity.AuthProvider;
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
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.OffsetDateTime;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class WorkspaceInvitationServiceTest {

    @Mock
    private WorkspaceRepository workspaceRepository;

    @Mock
    private WorkspaceMemberRepository workspaceMemberRepository;

    @Mock
    private WorkspaceInvitationRepository workspaceInvitationRepository;

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private WorkspaceInvitationService workspaceInvitationService;

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
        return workspace(id, creator, WorkspaceType.TEAM);
    }

    private Workspace workspace(Long id, User creator, WorkspaceType type) {
        Workspace workspace = Workspace.builder().name("우리팀").type(type).createdBy(creator).build();
        ReflectionTestUtils.setField(workspace, "id", id);
        return workspace;
    }

    private WorkspaceInvitation invitation(String code, Workspace workspace, User creator, OffsetDateTime expiresAt) {
        return WorkspaceInvitation.builder().workspace(workspace).code(code).expiresAt(expiresAt).createdBy(creator).build();
    }

    @Test
    @DisplayName("OWNER면 초대 코드를 생성한다")
    void createInvitation_owner_savesAndReturnsInvitation() {
        User me = user(1L);
        Workspace ws = workspace(10L, me);
        WorkspaceMember membership = WorkspaceMember.builder().workspace(ws).user(me).role(WorkspaceRole.OWNER).build();
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 1L)).thenReturn(Optional.of(membership));
        when(userRepository.findById(1L)).thenReturn(Optional.of(me));
        when(workspaceInvitationRepository.save(any(WorkspaceInvitation.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));

        WorkspaceInvitationResponse response = workspaceInvitationService.createInvitation(10L, 1L);

        assertThat(response.workspaceId()).isEqualTo(10L);
        assertThat(response.code()).isNotBlank();
        assertThat(response.expiresAt()).isAfter(OffsetDateTime.now());

        ArgumentCaptor<WorkspaceInvitation> captor = ArgumentCaptor.forClass(WorkspaceInvitation.class);
        verify(workspaceInvitationRepository).save(captor.capture());
        assertThat(captor.getValue().getCreatedBy()).isEqualTo(me);
    }

    @Test
    @DisplayName("PERSONAL 워크스페이스는 초대 코드를 생성할 수 없다")
    void createInvitation_personalWorkspace_throwsNotAllowed() {
        User me = user(1L);
        Workspace ws = workspace(10L, me, WorkspaceType.PERSONAL);
        WorkspaceMember membership = WorkspaceMember.builder().workspace(ws).user(me).role(WorkspaceRole.OWNER).build();
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 1L)).thenReturn(Optional.of(membership));

        assertThatThrownBy(() -> workspaceInvitationService.createInvitation(10L, 1L))
                .isInstanceOf(WorkspaceInvitationNotAllowedException.class);

        verify(workspaceInvitationRepository, never()).save(any(WorkspaceInvitation.class));
    }

    @Test
    @DisplayName("OWNER가 아니면 초대 코드 생성 시 403 예외를 던진다")
    void createInvitation_notOwner_throwsOwnerRequired() {
        User me = user(1L);
        Workspace ws = workspace(10L, me);
        WorkspaceMember membership = WorkspaceMember.builder().workspace(ws).user(me).role(WorkspaceRole.MEMBER).build();
        when(workspaceRepository.findById(10L)).thenReturn(Optional.of(ws));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 1L)).thenReturn(Optional.of(membership));

        assertThatThrownBy(() -> workspaceInvitationService.createInvitation(10L, 1L))
                .isInstanceOf(WorkspaceOwnerRequiredException.class);
    }

    @Test
    @DisplayName("존재하지 않는 워크스페이스면 초대 코드 생성 시 404 예외를 던진다")
    void createInvitation_workspaceNotFound_throwsNotFound() {
        when(workspaceRepository.findById(999L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> workspaceInvitationService.createInvitation(999L, 1L))
                .isInstanceOf(WorkspaceNotFoundException.class);
    }

    @Test
    @DisplayName("유효한 코드면 초대 정보를 조회할 수 있다")
    void getInvitation_valid_returnsResponse() {
        User creator = user(1L);
        Workspace ws = workspace(10L, creator);
        WorkspaceInvitation inv = invitation("abc-123", ws, creator, OffsetDateTime.now().plusDays(1));
        when(workspaceInvitationRepository.findByCode("abc-123")).thenReturn(Optional.of(inv));

        WorkspaceInvitationResponse response = workspaceInvitationService.getInvitation("abc-123");

        assertThat(response.workspaceId()).isEqualTo(10L);
        assertThat(response.workspaceName()).isEqualTo("우리팀");
    }

    @Test
    @DisplayName("존재하지 않는 코드면 404 예외를 던진다")
    void getInvitation_notFound_throwsNotFound() {
        when(workspaceInvitationRepository.findByCode("no-such-code")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> workspaceInvitationService.getInvitation("no-such-code"))
                .isInstanceOf(WorkspaceInvitationNotFoundException.class);
    }

    @Test
    @DisplayName("만료된 코드면 조회 시 예외를 던진다")
    void getInvitation_expired_throwsExpired() {
        User creator = user(1L);
        Workspace ws = workspace(10L, creator);
        WorkspaceInvitation inv = invitation("expired-code", ws, creator, OffsetDateTime.now().minusDays(1));
        when(workspaceInvitationRepository.findByCode("expired-code")).thenReturn(Optional.of(inv));

        assertThatThrownBy(() -> workspaceInvitationService.getInvitation("expired-code"))
                .isInstanceOf(WorkspaceInvitationExpiredException.class);
    }

    @Test
    @DisplayName("유효한 코드로 수락하면 MEMBER로 가입 처리한다")
    void accept_valid_addsMemberAndReturnsWorkspace() {
        User creator = user(1L);
        Workspace ws = workspace(10L, creator);
        WorkspaceInvitation inv = invitation("abc-123", ws, creator, OffsetDateTime.now().plusDays(1));
        User joiner = user(2L);
        when(workspaceInvitationRepository.findByCode("abc-123")).thenReturn(Optional.of(inv));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 2L)).thenReturn(Optional.empty());
        when(userRepository.findById(2L)).thenReturn(Optional.of(joiner));
        when(workspaceMemberRepository.save(any(WorkspaceMember.class))).thenAnswer(invocation -> invocation.getArgument(0));

        WorkspaceResponse response = workspaceInvitationService.accept("abc-123", 2L);

        assertThat(response.id()).isEqualTo(10L);
        assertThat(response.role()).isEqualTo(WorkspaceRole.MEMBER);

        ArgumentCaptor<WorkspaceMember> captor = ArgumentCaptor.forClass(WorkspaceMember.class);
        verify(workspaceMemberRepository).save(captor.capture());
        assertThat(captor.getValue().getUser()).isEqualTo(joiner);
        assertThat(captor.getValue().getRole()).isEqualTo(WorkspaceRole.MEMBER);
    }

    @Test
    @DisplayName("만료된 코드로 수락하면 예외를 던지고 가입시키지 않는다")
    void accept_expired_throwsExpired() {
        User creator = user(1L);
        Workspace ws = workspace(10L, creator);
        WorkspaceInvitation inv = invitation("expired-code", ws, creator, OffsetDateTime.now().minusDays(1));
        when(workspaceInvitationRepository.findByCode("expired-code")).thenReturn(Optional.of(inv));

        assertThatThrownBy(() -> workspaceInvitationService.accept("expired-code", 2L))
                .isInstanceOf(WorkspaceInvitationExpiredException.class);

        verify(workspaceMemberRepository, never()).save(any(WorkspaceMember.class));
    }

    @Test
    @DisplayName("이미 가입된 워크스페이스면 수락 시 예외를 던진다")
    void accept_alreadyMember_throwsIllegalArgument() {
        User creator = user(1L);
        Workspace ws = workspace(10L, creator);
        WorkspaceInvitation inv = invitation("abc-123", ws, creator, OffsetDateTime.now().plusDays(1));
        WorkspaceMember existing = WorkspaceMember.builder().workspace(ws).user(user(2L)).role(WorkspaceRole.MEMBER).build();
        when(workspaceInvitationRepository.findByCode("abc-123")).thenReturn(Optional.of(inv));
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(10L, 2L)).thenReturn(Optional.of(existing));

        assertThatThrownBy(() -> workspaceInvitationService.accept("abc-123", 2L))
                .isInstanceOf(IllegalArgumentException.class);

        verify(workspaceMemberRepository, never()).save(any(WorkspaceMember.class));
    }
}
