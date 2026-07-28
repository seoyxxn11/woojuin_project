package com.ssafy.woojuin.domain.workspace.exception;

public class WorkspaceNotFoundException extends RuntimeException {

    public WorkspaceNotFoundException(Long workspaceId) {
        super("COMMON_404: 워크스페이스를 찾을 수 없습니다 (id=" + workspaceId + ")");
    }
}
