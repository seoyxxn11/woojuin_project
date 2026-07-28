package com.ssafy.woojuin.domain.workspace.exception;

/** 로그인은 했지만 해당 워크스페이스 멤버가 아닌 경우. */
public class WorkspaceMemberRequiredException extends RuntimeException {

    public WorkspaceMemberRequiredException(Long workspaceId) {
        super("COMMON_403: 워크스페이스 멤버가 아닙니다 (workspaceId=" + workspaceId + ")");
    }
}
