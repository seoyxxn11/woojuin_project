package com.ssafy.woojuin.domain.workspace.controller;

import com.ssafy.woojuin.domain.workspace.exception.WorkspaceMemberRequiredException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceNotFoundException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceOwnerRequiredException;
import com.ssafy.woojuin.domain.workspace.dto.WorkspaceResponse;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceRole;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceType;
import com.ssafy.woojuin.domain.workspace.service.WorkspaceService;
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

import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = WorkspaceController.class, excludeAutoConfiguration = OAuth2ClientAutoConfiguration.class)
@AutoConfigureMockMvc(addFilters = false)
@Import({CurrentUserResolver.class, AuthenticationAspect.class})
@EnableAspectJAutoProxy
class WorkspaceControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private WorkspaceService workspaceService;

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private void authenticateAs(Long userId) {
        SecurityContextHolder.getContext()
                .setAuthentication(new UsernamePasswordAuthenticationToken(userId, null, List.of()));
    }

    @Test
    void 인증되지_않은_생성_요청은_공통형식_401() throws Exception {
        mockMvc.perform(post("/api/workspaces")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"우리팀\",\"type\":\"TEAM\"}"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.status").value(401));

        verify(workspaceService, never()).create(any(), any());
    }

    @Test
    void 생성_성공하면_201과_생성된_워크스페이스() throws Exception {
        authenticateAs(1L);
        when(workspaceService.create(eq(1L), any()))
                .thenReturn(new WorkspaceResponse(10L, "우리팀", WorkspaceType.TEAM, WorkspaceRole.OWNER));

        mockMvc.perform(post("/api/workspaces")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"우리팀\",\"type\":\"TEAM\"}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.status").value(201))
                .andExpect(jsonPath("$.data.id").value(10))
                .andExpect(jsonPath("$.data.role").value("OWNER"));
    }

    @Test
    void 내_워크스페이스_목록_조회() throws Exception {
        authenticateAs(1L);
        when(workspaceService.list(1L)).thenReturn(
                List.of(new WorkspaceResponse(10L, "우리팀", WorkspaceType.TEAM, WorkspaceRole.OWNER)));

        mockMvc.perform(get("/api/workspaces"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].id").value(10));
    }

    @Test
    void 존재하지_않는_워크스페이스_조회는_공통형식_404() throws Exception {
        authenticateAs(1L);
        when(workspaceService.get(999L, 1L)).thenThrow(new WorkspaceNotFoundException(999L));

        mockMvc.perform(get("/api/workspaces/999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404));
    }

    @Test
    void 멤버가_아니면_조회시_공통형식_403() throws Exception {
        authenticateAs(1L);
        when(workspaceService.get(10L, 1L)).thenThrow(new WorkspaceMemberRequiredException(10L));

        mockMvc.perform(get("/api/workspaces/10"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.status").value(403));
    }

    @Test
    void OWNER_아니면_수정시_공통형식_403() throws Exception {
        authenticateAs(1L);
        when(workspaceService.update(eq(10L), eq(1L), any())).thenThrow(new WorkspaceOwnerRequiredException(10L));

        mockMvc.perform(patch("/api/workspaces/10")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"새이름\"}"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.status").value(403));
    }

    @Test
    void 삭제_성공하면_200과_빈_데이터() throws Exception {
        authenticateAs(1L);

        mockMvc.perform(delete("/api/workspaces/10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value(200))
                .andExpect(jsonPath("$.data").doesNotExist());

        verify(workspaceService).delete(10L, 1L);
    }
}
