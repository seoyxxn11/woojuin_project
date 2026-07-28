package com.ssafy.woojuin.global.security.aop;

import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.springframework.stereotype.Component;

/**
 * @AuthenticatedUser 붙은 메서드 실행 전에 인증 여부를 검사한다.
 * 실제 판단 로직은 CurrentUserResolver에 있고, 여기서는 그걸 호출해 트리거만 한다.
 */
@Aspect
@Component
public class AuthenticationAspect {

    private final CurrentUserResolver currentUserResolver;

    public AuthenticationAspect(CurrentUserResolver currentUserResolver) {
        this.currentUserResolver = currentUserResolver;
    }

    @Before("@annotation(com.ssafy.woojuin.global.security.aop.AuthenticatedUser)")
    public void checkAuthenticated() {
        currentUserResolver.resolveUserId();
    }
}
