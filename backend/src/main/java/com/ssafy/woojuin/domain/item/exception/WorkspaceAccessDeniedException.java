package com.ssafy.woojuin.domain.item.exception;

public class WorkspaceAccessDeniedException extends RuntimeException {

    public WorkspaceAccessDeniedException(Long workspaceId) {
        super("COMMON_403: 워크스페이스 멤버가 아닙니다 (workspaceId=" + workspaceId + ")");
    }
}
