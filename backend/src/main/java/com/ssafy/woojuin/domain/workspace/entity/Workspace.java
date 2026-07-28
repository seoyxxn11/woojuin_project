package com.ssafy.woojuin.domain.workspace.entity;

import com.ssafy.woojuin.domain.auth.entity.User;
import com.ssafy.woojuin.global.common.BaseTimeEntity;
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
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "workspaces")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Workspace extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 100)
    private String name;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private WorkspaceType type;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "created_by", nullable = false)
    private User createdBy;

    @Builder
    public Workspace(String name, WorkspaceType type, User createdBy) {
        this.name = name;
        this.type = type;
        this.createdBy = createdBy;
    }

    public void updateName(String name) {
        this.name = name;
    }
}
