package com.ssafy.woojuin.domain.workspace.repository;

import com.ssafy.woojuin.domain.workspace.entity.WorkspaceInvitation;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface WorkspaceInvitationRepository extends JpaRepository<WorkspaceInvitation, Long> {

    Optional<WorkspaceInvitation> findByCode(String code);

    List<WorkspaceInvitation> findByWorkspaceId(Long workspaceId);
}
