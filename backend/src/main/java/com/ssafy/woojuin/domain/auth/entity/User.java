package com.ssafy.woojuin.domain.auth.entity;

import com.ssafy.woojuin.global.common.BaseTimeEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * LOCAL 유저는 passwordHash 필수 + providerId NULL, OAuth 유저는 반대.
 * (ERD 설계 노트 CHECK 제약 참고, 검증은 서비스 레이어에서 수행)
 */
@Entity
@Table(name = "users", uniqueConstraints = @UniqueConstraint(columnNames = {"provider", "provider_id"}))
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class User extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 255)
    private String email;

    @Column(name = "password_hash")
    private String passwordHash;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private AuthProvider provider;

    @Column(name = "provider_id", length = 100)
    private String providerId;

    @Column(name = "email_verified", nullable = false)
    private boolean emailVerified;

    @Column(nullable = false, length = 50)
    private String nickname;

    @Column(name = "profile_image_url", columnDefinition = "TEXT")
    private String profileImageUrl;

    /** 가입 시 자동 생성되는 PERSONAL 워크스페이스의 id. 생성 전에는 null. */
    @Column(name = "personal_workspace_id")
    private Long personalWorkspaceId;

    /** 프로필 아바타 색상. 가입 시 기본값은 WHITE, 나중에 프로필 설정에서 바꿀 수 있게 할 예정. */
    @Enumerated(EnumType.STRING)
    @Column(name = "avatar_color", nullable = false, length = 20)
    private AvatarColor avatarColor = AvatarColor.WHITE;

    @Builder
    public User(String email, String passwordHash, AuthProvider provider, String providerId,
                boolean emailVerified, String nickname, String profileImageUrl) {
        this.email = email;
        this.passwordHash = passwordHash;
        this.provider = provider;
        this.providerId = providerId;
        this.emailVerified = emailVerified;
        this.nickname = nickname;
        this.profileImageUrl = profileImageUrl;
    }

    public void updateProfile(String nickname, String profileImageUrl, AvatarColor avatarColor) {
        this.nickname = nickname;
        this.profileImageUrl = profileImageUrl;
        this.avatarColor = avatarColor;
    }

    public void assignPersonalWorkspace(Long workspaceId) {
        this.personalWorkspaceId = workspaceId;
    }
}
