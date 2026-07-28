package com.ssafy.woojuin.domain.workspace.event;

/**
 * 워크스페이스가 생성됐을 때 발행. 다른 도메인(예: 카테고리 기본값 시드)이 워크스페이스
 * 생성 코드를 건드리지 않고 이 이벤트에 반응하게 하려는 접점이다.
 *
 * <p>동기 @EventListener로 소비되면 생성 트랜잭션 안에서 처리되어 원자성이 보장된다
 * (시드 실패 시 워크스페이스 생성도 롤백).
 */
public record WorkspaceCreatedEvent(Long workspaceId) {
}
