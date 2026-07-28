package com.ssafy.woojuin.domain.workspace.controller;

import com.ssafy.woojuin.domain.workspace.dto.WorkspaceMemberResponse;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceRole;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceLastOwnerException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceMemberNotFoundException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceOwnerRequiredException;
import com.ssafy.woojuin.domain.workspace.service.WorkspaceMemberService;
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
import org.springframework.http.MediaType;
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
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = WorkspaceMemberController.class, excludeAutoConfiguration = OAuth2ClientAutoConfiguration.class)
@AutoConfigureMockMvc(addFilters = false)
@Import({CurrentUserResolver.class, AuthenticationAspect.class})
@EnableAspectJAutoProxy
class WorkspaceMemberControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private WorkspaceMemberService workspaceMemberService;

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private void authenticateAs(Long userId) {
        SecurityContextHolder.getContext()
                .setAuthentication(new UsernamePasswordAuthenticationToken(userId, null, List.of()));
    }

    @Test
    void 인증되지_않은_목록_조회는_공통형식_401() throws Exception {
        mockMvc.perform(get("/api/workspaces/10/members"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.status").value(401));

        verify(workspaceMemberService, never()).list(any(), any());
    }

    @Test
    void 멤버_목록_조회_성공() throws Exception {
        authenticateAs(1L);
        when(workspaceMemberService.list(10L, 1L)).thenReturn(List.of(
                new WorkspaceMemberResponse(1L, "우주인", "test@woojuin.com", WorkspaceRole.OWNER, OffsetDateTime.now())));

        mockMvc.perform(get("/api/workspaces/10/members"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].role").value("OWNER"));
    }

    @Test
    void OWNER_아니면_역할변경시_공통형식_403() throws Exception {
        authenticateAs(1L);
        when(workspaceMemberService.updateRole(eq(10L), eq(2L), eq(1L), any()))
                .thenThrow(new WorkspaceOwnerRequiredException(10L));

        mockMvc.perform(patch("/api/workspaces/10/members/2")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"role\":\"OWNER\"}"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.status").value(403));
    }

    @Test
    void 대상이_멤버가_아니면_역할변경시_공통형식_404() throws Exception {
        authenticateAs(1L);
        when(workspaceMemberService.updateRole(eq(10L), eq(999L), eq(1L), any()))
                .thenThrow(new WorkspaceMemberNotFoundException(10L, 999L));

        mockMvc.perform(patch("/api/workspaces/10/members/999")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"role\":\"MEMBER\"}"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404));
    }

    @Test
    void 마지막_OWNER_강등시도는_공통형식_400() throws Exception {
        authenticateAs(1L);
        when(workspaceMemberService.updateRole(eq(10L), eq(1L), eq(1L), any()))
                .thenThrow(new WorkspaceLastOwnerException(10L));

        mockMvc.perform(patch("/api/workspaces/10/members/1")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"role\":\"MEMBER\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.status").value(400));
    }

    @Test
    void 역할변경_성공하면_200() throws Exception {
        authenticateAs(1L);
        when(workspaceMemberService.updateRole(eq(10L), eq(2L), eq(1L), any())).thenReturn(
                new WorkspaceMemberResponse(2L, "닉네임", "a@woojuin.com", WorkspaceRole.OWNER, OffsetDateTime.now()));

        mockMvc.perform(patch("/api/workspaces/10/members/2")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"role\":\"OWNER\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.role").value("OWNER"));
    }

    @Test
    void 멤버_제거_성공하면_200() throws Exception {
        authenticateAs(1L);

        mockMvc.perform(delete("/api/workspaces/10/members/2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value(200));

        verify(workspaceMemberService).remove(10L, 2L, 1L);
    }

    @Test
    void 마지막_OWNER_탈퇴시도는_공통형식_400() throws Exception {
        authenticateAs(1L);
        org.mockito.Mockito.doThrow(new WorkspaceLastOwnerException(10L))
                .when(workspaceMemberService).remove(10L, 1L, 1L);

        mockMvc.perform(delete("/api/workspaces/10/members/1"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.status").value(400));
    }
}
