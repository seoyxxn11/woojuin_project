package com.ssafy.woojuin.global.security.aop;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 인증된 사용자만 호출할 수 있는 메서드에 붙인다.
 * 워크스페이스 OWNER/MEMBER 같은 역할 기반 체크가 필요해지면
 * 별도 어노테이션(@RequireWorkspaceRole 등)과 Aspect로 확장한다.
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface AuthenticatedUser {
}
