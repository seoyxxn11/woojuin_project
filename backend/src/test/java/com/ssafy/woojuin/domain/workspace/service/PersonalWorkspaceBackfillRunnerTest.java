package com.ssafy.woojuin.domain.workspace.service;

import com.ssafy.woojuin.domain.auth.entity.AuthProvider;
import com.ssafy.woojuin.domain.auth.entity.User;
import com.ssafy.woojuin.domain.auth.repository.UserRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.boot.DefaultApplicationArguments;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class PersonalWorkspaceBackfillRunnerTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private WorkspaceService workspaceService;

    @InjectMocks
    private PersonalWorkspaceBackfillRunner personalWorkspaceBackfillRunner;

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

    @Test
    @DisplayName("모든 유저에 대해 개인 워크스페이스 생성을 시도한다")
    void run_forEveryUser_ensuresPersonalWorkspace() {
        when(userRepository.findAll()).thenReturn(List.of(user(1L), user(2L)));

        personalWorkspaceBackfillRunner.run(new DefaultApplicationArguments());

        verify(workspaceService).ensurePersonalWorkspace(1L);
        verify(workspaceService).ensurePersonalWorkspace(2L);
    }
}
