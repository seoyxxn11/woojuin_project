package com.ssafy.woojuin.domain.workspace.exception;

/** 멤버이긴 하지만 OWNER가 아니어서 수정/삭제 같은 소유자 전용 작업을 할 수 없는 경우. */
public class WorkspaceOwnerRequiredException extends RuntimeException {

    public WorkspaceOwnerRequiredException(Long workspaceId) {
        super("COMMON_403: 워크스페이스 OWNER만 가능합니다 (workspaceId=" + workspaceId + ")");
    }
}
