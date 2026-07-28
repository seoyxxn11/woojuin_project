package com.ssafy.woojuin.domain.workspace.exception;

/** 워크스페이스에 OWNER가 0명이 되는 상황(마지막 OWNER 강등/제거)을 막기 위해 던진다. */
public class WorkspaceLastOwnerException extends RuntimeException {

    public WorkspaceLastOwnerException(Long workspaceId) {
        super("COMMON_400: 마지막 OWNER는 강등하거나 제거할 수 없습니다 (workspaceId=" + workspaceId
                + "). 다른 멤버를 먼저 OWNER로 지정하세요.");
    }
}
