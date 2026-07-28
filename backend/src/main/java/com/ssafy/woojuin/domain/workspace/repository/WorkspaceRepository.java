package com.ssafy.woojuin.domain.workspace.repository;

import com.ssafy.woojuin.domain.workspace.entity.Workspace;
import org.springframework.data.jpa.repository.JpaRepository;

public interface WorkspaceRepository extends JpaRepository<Workspace, Long> {
}
