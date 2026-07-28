package com.ssafy.woojuin.domain.auth.event;

/**
 * 신규 유저가 가입했을 때 발행. 워크스페이스 도메인이 회원가입 코드를 건드리지 않고
 * PERSONAL 워크스페이스 자동 생성에 반응하게 하려는 접점이다 (WorkspaceCreatedEvent와 대칭).
 */
public record UserSignedUpEvent(Long userId) {
}
