package com.ssafy.woojuin.domain.workspace.entity;

import com.ssafy.woojuin.domain.auth.entity.User;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;

@Entity
@Table(name = "workspace_invitations")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class WorkspaceInvitation {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "workspace_id", nullable = false)
    private Workspace workspace;

    @Column(nullable = false, unique = true, length = 64)
    private String code;

    @Column(name = "expires_at", nullable = false)
    private OffsetDateTime expiresAt;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "created_by", nullable = false)
    private User createdBy;

    @Builder
    public WorkspaceInvitation(Workspace workspace, String code, OffsetDateTime expiresAt, User createdBy) {
        this.workspace = workspace;
        this.code = code;
        this.expiresAt = expiresAt;
        this.createdBy = createdBy;
    }
}
