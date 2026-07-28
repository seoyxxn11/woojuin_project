package com.ssafy.woojuin.domain.workspace.controller;

import com.ssafy.woojuin.domain.workspace.dto.WorkspaceInvitationResponse;
import com.ssafy.woojuin.domain.workspace.dto.WorkspaceResponse;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceRole;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceType;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceInvitationExpiredException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceInvitationNotFoundException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceOwnerRequiredException;
import com.ssafy.woojuin.domain.workspace.service.WorkspaceInvitationService;
import com.ssafy.woojuin.global.security.aop.AuthenticationAspect;
import com.ssafy.woojuin.global.security.aop.CurrentUserResolver;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.security.oauth2.client.servlet.OAuth2ClientAutoConfiguration;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.EnableAspectJAutoProxy;
import org.springframework.context.annotation.Import;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;

import java.time.OffsetDateTime;
import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = {WorkspaceInvitationController.class, InvitationController.class},
        excludeAutoConfiguration = OAuth2ClientAutoConfiguration.class)
@AutoConfigureMockMvc(addFilters = false)
@Import({CurrentUserResolver.class, AuthenticationAspect.class})
@EnableAspectJAutoProxy
class WorkspaceInvitationControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private WorkspaceInvitationService workspaceInvitationService;

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private void authenticateAs(Long userId) {
        SecurityContextHolder.getContext()
                .setAuthentication(new UsernamePasswordAuthenticationToken(userId, null, List.of()));
    }

    @Test
    void 인증되지_않은_초대생성_요청은_공통형식_401() throws Exception {
        mockMvc.perform(post("/api/workspaces/10/invitations"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.status").value(401));

        verify(workspaceInvitationService, never()).createInvitation(any(), any());
    }

    @Test
    void OWNER_아니면_초대생성시_공통형식_403() throws Exception {
        authenticateAs(1L);
        when(workspaceInvitationService.createInvitation(10L, 1L)).thenThrow(new WorkspaceOwnerRequiredException(10L));

        mockMvc.perform(post("/api/workspaces/10/invitations"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.status").value(403));
    }

    @Test
    void 초대생성_성공하면_201과_코드() throws Exception {
        authenticateAs(1L);
        when(workspaceInvitationService.createInvitation(10L, 1L)).thenReturn(
                new WorkspaceInvitationResponse("abc-123", 10L, "우리팀", OffsetDateTime.now().plusDays(7)));

        mockMvc.perform(post("/api/workspaces/10/invitations"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.code").value("abc-123"));
    }

    @Test
    void 초대코드_조회는_인증없이도_가능() throws Exception {
        when(workspaceInvitationService.getInvitation("abc-123")).thenReturn(
                new WorkspaceInvitationResponse("abc-123", 10L, "우리팀", OffsetDateTime.now().plusDays(7)));

        mockMvc.perform(get("/api/invitations/abc-123"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.workspaceName").value("우리팀"));
    }

    @Test
    void 만료된_초대코드_조회는_공통형식_400() throws Exception {
        when(workspaceInvitationService.getInvitation("expired")).thenThrow(new WorkspaceInvitationExpiredException("expired"));

        mockMvc.perform(get("/api/invitations/expired"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.status").value(400));
    }

    @Test
    void 없는_초대코드_조회는_공통형식_404() throws Exception {
        when(workspaceInvitationService.getInvitation("no-such")).thenThrow(new WorkspaceInvitationNotFoundException("no-such"));

        mockMvc.perform(get("/api/invitations/no-such"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404));
    }

    @Test
    void 인증되지_않은_수락_요청은_공통형식_401() throws Exception {
        mockMvc.perform(post("/api/invitations/abc-123/accept"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.status").value(401));

        verify(workspaceInvitationService, never()).accept(any(), any());
    }

    @Test
    void 수락_성공하면_200과_가입한_워크스페이스() throws Exception {
        authenticateAs(2L);
        when(workspaceInvitationService.accept(eq("abc-123"), eq(2L)))
                .thenReturn(new WorkspaceResponse(10L, "우리팀", WorkspaceType.TEAM, WorkspaceRole.MEMBER));

        mockMvc.perform(post("/api/invitations/abc-123/accept"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.role").value("MEMBER"));
    }
}
