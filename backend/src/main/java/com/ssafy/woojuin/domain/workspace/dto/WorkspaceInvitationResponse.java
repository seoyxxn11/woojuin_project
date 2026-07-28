package com.ssafy.woojuin.domain.workspace.dto;

import com.ssafy.woojuin.domain.workspace.entity.WorkspaceInvitation;

import java.time.OffsetDateTime;

public record WorkspaceInvitationResponse(String code, Long workspaceId, String workspaceName,
                                           OffsetDateTime expiresAt) {

    public static WorkspaceInvitationResponse of(WorkspaceInvitation invitation) {
        return new WorkspaceInvitationResponse(invitation.getCode(), invitation.getWorkspace().getId(),
                invitation.getWorkspace().getName(), invitation.getExpiresAt());
    }
}
