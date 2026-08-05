package com.ssafy.woojuin.domain.ai.engine.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * 정식 카테고리의 앵커 메타. 승격 카테고리 재사용 매칭(같은 대상 데이터 → 승격 카테고리 연결)에
 * 쓴다. 기존 categories 테이블을 건드리지 않고 격리한다. SEED 카테고리는 행이 없어도 된다.
 * categoryId가 곧 PK(카테고리 1개당 앵커 1개).
 */
@Getter
@Entity
@Table(name = "category_anchors")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class CategoryAnchor {

    public static final String SEED = "SEED";
    public static final String AI_PROMOTED = "AI_PROMOTED";

    @Id
    private Long categoryId;

    @Column(nullable = false, length = 20)
    private String origin;

    @Column(length = 20)
    private String anchorType;

    @Column(length = 100)
    private String normalizedAnchorName;

    @Builder
    private CategoryAnchor(Long categoryId, String origin, String anchorType,
            String normalizedAnchorName) {
        this.categoryId = categoryId;
        this.origin = origin;
        this.anchorType = anchorType;
        this.normalizedAnchorName = normalizedAnchorName;
    }
}
