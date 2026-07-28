package com.ssafy.woojuin.domain.workspace.dto;

import com.ssafy.woojuin.domain.workspace.entity.WorkspaceMember;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceRole;

import java.time.OffsetDateTime;

public record WorkspaceMemberResponse(Long userId, String nickname, String email, WorkspaceRole role,
                                       OffsetDateTime joinedAt) {

    public static WorkspaceMemberResponse of(WorkspaceMember member) {
        return new WorkspaceMemberResponse(member.getUser().getId(), member.getUser().getNickname(),
                member.getUser().getEmail(), member.getRole(), member.getJoinedAt());
    }
}
