package com.ssafy.woojuin.domain.workspace.dto;

import com.ssafy.woojuin.domain.workspace.entity.WorkspaceType;

public record WorkspaceCreateRequest(String name, WorkspaceType type) {
}
