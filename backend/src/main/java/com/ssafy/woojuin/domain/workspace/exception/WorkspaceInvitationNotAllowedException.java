package com.ssafy.woojuin.domain.workspace.exception;

/** PERSONAL 워크스페이스처럼 초대 자체가 허용되지 않는 유형일 때 던진다. */
public class WorkspaceInvitationNotAllowedException extends RuntimeException {

    public WorkspaceInvitationNotAllowedException(Long workspaceId) {
        super("COMMON_400: 개인 워크스페이스는 멤버를 초대할 수 없습니다 (workspaceId=" + workspaceId + ")");
    }
}
