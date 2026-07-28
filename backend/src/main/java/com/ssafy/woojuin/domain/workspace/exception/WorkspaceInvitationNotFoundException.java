package com.ssafy.woojuin.domain.workspace.exception;

public class WorkspaceInvitationNotFoundException extends RuntimeException {

    public WorkspaceInvitationNotFoundException(String code) {
        super("COMMON_404: 초대 코드를 찾을 수 없습니다 (code=" + code + ")");
    }
}
