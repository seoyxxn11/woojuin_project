package com.ssafy.woojuin.domain.category.entity;

import com.ssafy.woojuin.global.common.BaseTimeEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
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
 * 카테고리. 워크스페이스마다 별도로 존재하며(같은 이름이라도 다른 레코드), 기본 11개가
 * 시드된 뒤 사용자가 추가/수정/삭제한다.
 *
 * <p>workspaceId는 Item과 같은 방식으로 JPA 연관관계 없이 순수 FK 컬럼으로 둔다 —
 * 비동기 가공 파이프라인이 Workspace 엔티티를 로드하지 않고 id만으로 다루기 때문.
 */
@Getter
@Entity
@Table(name = "categories",
        uniqueConstraints = @UniqueConstraint(columnNames = {"workspace_id", "name"}))
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Category extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long workspaceId;

    @Column(nullable = false, length = 50)
    private String name;

    // 카드/별자리 색(hex, 예 "#C9B8FF"). 기존 데이터 호환을 위해 nullable로 두고,
    // 시드·생성 시 채우며 기존 행은 CategoryColorBackfill이 기동 시 채운다.
    @Column(length = 20)
    private String color;

    @Builder
    private Category(Long workspaceId, String name, String color) {
        this.workspaceId = workspaceId;
        this.name = name;
        this.color = color;
    }

    public void rename(String name) {
        this.name = name;
    }

    /** null 인자는 "값 없음"이라 무시한다(기존 색을 지우지 않음). */
    public void applyColor(String color) {
        if (color != null) {
            this.color = color;
        }
    }
}
