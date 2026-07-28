package com.ssafy.woojuin.global.security.aop;

import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

@Component
public class CurrentUserResolver {

    //현재 세션에 저장되어 있는 Authentication의 정보를 가져와서 userId를 반환한다.
    public Long resolveUserId() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !(authentication.getPrincipal() instanceof Long userId)) {
            throw new AccessDeniedException("인증이 필요합니다");
        }
        return userId;
    }
}
