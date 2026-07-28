package com.ssafy.woojuin.global.security.aop;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class CurrentUserResolverTest {

    private final CurrentUserResolver resolver = new CurrentUserResolver();

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    @Test
    @DisplayName("JwtAuthenticationFilter가 설정한 Long principal이면 userId를 반환한다")
    void resolveUserId_authenticatedWithLongPrincipal_returnsUserId() {
        SecurityContextHolder.getContext()
                .setAuthentication(new UsernamePasswordAuthenticationToken(1L, null, List.of()));

        assertThat(resolver.resolveUserId()).isEqualTo(1L);
    }

    @Test
    @DisplayName("인증 정보가 없으면 AccessDeniedException을 던진다")
    void resolveUserId_noAuthentication_throwsAccessDeniedException() {
        SecurityContextHolder.clearContext();

        assertThatThrownBy(resolver::resolveUserId).isInstanceOf(AccessDeniedException.class);
    }

    @Test
    @DisplayName("익명 사용자(비로그인)면 AccessDeniedException을 던진다")
    void resolveUserId_anonymousUser_throwsAccessDeniedException() {
        SecurityContextHolder.getContext().setAuthentication(new AnonymousAuthenticationToken(
                "key", "anonymousUser", List.of(new SimpleGrantedAuthority("ROLE_ANONYMOUS"))));

        assertThatThrownBy(resolver::resolveUserId).isInstanceOf(AccessDeniedException.class);
    }
}
