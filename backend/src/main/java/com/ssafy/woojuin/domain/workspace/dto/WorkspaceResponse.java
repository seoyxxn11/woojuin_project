package com.ssafy.woojuin.domain.workspace.dto;

import com.ssafy.woojuin.domain.workspace.entity.Workspace;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceRole;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceType;

public record WorkspaceResponse(Long id, String name, WorkspaceType type, WorkspaceRole role) {

    public static WorkspaceResponse of(Workspace workspace, WorkspaceRole role) {
        return new WorkspaceResponse(workspace.getId(), workspace.getName(), workspace.getType(), role);
    }
}
