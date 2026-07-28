package com.ssafy.woojuin.domain.category.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.ssafy.woojuin.domain.category.dto.CategoryResponse;
import com.ssafy.woojuin.domain.category.service.CategoryService;
import com.ssafy.woojuin.global.security.aop.AuthenticationAspect;
import com.ssafy.woojuin.global.security.aop.CurrentUserResolver;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.security.oauth2.client.servlet.OAuth2ClientAutoConfiguration;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.EnableAspectJAutoProxy;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(controllers = CategoryController.class, excludeAutoConfiguration = OAuth2ClientAutoConfiguration.class)
@AutoConfigureMockMvc(addFilters = false)
@org.springframework.context.annotation.Import({CurrentUserResolver.class, AuthenticationAspect.class})
@EnableAspectJAutoProxy
class CategoryControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private CategoryService categoryService;

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private void authenticateAs(Long userId) {
        SecurityContextHolder.getContext()
                .setAuthentication(new UsernamePasswordAuthenticationToken(userId, null, List.of()));
    }

    @Test
    void 인증되지_않은_생성은_공통형식_401() throws Exception {
        mockMvc.perform(post("/api/workspaces/1/categories")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"새것\"}"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.status").value(401));

        verify(categoryService, never()).create(any(), any(), any());
    }

    @Test
    void 카테고리_목록_조회() throws Exception {
        authenticateAs(1L);
        when(categoryService.list(1L, 1L, false)).thenReturn(List.of(new CategoryResponse(10L, "학습·지식", "#8FB4FF")));

        mockMvc.perform(get("/api/workspaces/1/categories"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].categoryId").value(10))
                .andExpect(jsonPath("$.data[0].name").value("학습·지식"))
                .andExpect(jsonPath("$.data[0].color").value("#8FB4FF"));
    }

    @Test
    void 생성_성공하면_201() throws Exception {
        authenticateAs(1L);
        when(categoryService.create(eq(1L), eq(1L), eq("새것")))
                .thenReturn(new CategoryResponse(20L, "새것", "#C9B8FF"));

        mockMvc.perform(post("/api/workspaces/1/categories")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"새것\"}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.status").value(201))
                .andExpect(jsonPath("$.data.categoryId").value(20));
    }

    @Test
    void 빈_이름은_공통형식_400() throws Exception {
        authenticateAs(1L);

        mockMvc.perform(post("/api/workspaces/1/categories")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.status").value(400));

        verify(categoryService, never()).create(any(), any(), any());
    }

    @Test
    void 기타_삭제는_공통형식_400() throws Exception {
        authenticateAs(1L);
        doThrow(new IllegalArgumentException("\"기타\" 카테고리는 삭제할 수 없습니다"))
                .when(categoryService).delete(1L, 1L, 9L);

        mockMvc.perform(delete("/api/workspaces/1/categories/9"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.status").value(400));
    }

    @Test
    void 삭제_성공하면_200() throws Exception {
        authenticateAs(1L);

        mockMvc.perform(delete("/api/workspaces/1/categories/5"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value(200));

        verify(categoryService).delete(1L, 1L, 5L);
    }
}
