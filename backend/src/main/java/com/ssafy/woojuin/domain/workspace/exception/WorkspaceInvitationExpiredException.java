package com.ssafy.woojuin.domain.workspace.exception;

public class WorkspaceInvitationExpiredException extends RuntimeException {

    public WorkspaceInvitationExpiredException(String code) {
        super("COMMON_400: 만료된 초대 코드입니다 (code=" + code + ")");
    }
}
