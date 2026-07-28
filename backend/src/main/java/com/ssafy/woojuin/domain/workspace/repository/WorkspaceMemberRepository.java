package com.ssafy.woojuin.domain.workspace.repository;

import com.ssafy.woojuin.domain.workspace.entity.WorkspaceMember;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceRole;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface WorkspaceMemberRepository extends JpaRepository<WorkspaceMember, Long> {

    List<WorkspaceMember> findByWorkspaceId(Long workspaceId);

    List<WorkspaceMember> findByUserId(Long userId);

    Optional<WorkspaceMember> findByWorkspaceIdAndUserId(Long workspaceId, Long userId);

    long countByWorkspaceIdAndRole(Long workspaceId, WorkspaceRole role);
}
