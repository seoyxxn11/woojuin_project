package com.ssafy.woojuin.domain.workspace.entity;

import com.ssafy.woojuin.domain.auth.entity.User;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;

@Entity
@Table(name = "workspace_members", uniqueConstraints = @UniqueConstraint(columnNames = {"workspace_id", "user_id"}))
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class WorkspaceMember {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "workspace_id", nullable = false)
    private Workspace workspace;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private WorkspaceRole role;

    @Column(name = "joined_at", nullable = false)
    private OffsetDateTime joinedAt;

    @Builder
    public WorkspaceMember(Workspace workspace, User user, WorkspaceRole role) {
        this.workspace = workspace;
        this.user = user;
        this.role = role;
        this.joinedAt = OffsetDateTime.now();
    }

    public void updateRole(WorkspaceRole role) {
        this.role = role;
    }
}
