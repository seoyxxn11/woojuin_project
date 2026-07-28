package com.ssafy.woojuin.domain.workspace.exception;

/** 대상 유저가 해당 워크스페이스의 멤버가 아닌 경우 (요청자 본인의 멤버십 여부와는 별개). */
public class WorkspaceMemberNotFoundException extends RuntimeException {

    public WorkspaceMemberNotFoundException(Long workspaceId, Long userId) {
        super("COMMON_404: 워크스페이스 멤버를 찾을 수 없습니다 (workspaceId=" + workspaceId + ", userId=" + userId + ")");
    }
}
