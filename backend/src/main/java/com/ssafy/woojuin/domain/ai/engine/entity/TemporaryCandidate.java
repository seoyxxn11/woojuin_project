package com.ssafy.woojuin.domain.ai.engine.entity;

import com.ssafy.woojuin.global.common.BaseTimeEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * 임시 후보(TemporaryCandidate). 반복되는 핵심 대상을 모아 supportCount가 기준(3) 이상이면
 * 정식 카테고리로 승격된다. AI 서버는 상태를 저장하지 않으므로 이 상태의 소유자는 백엔드다.
 *
 * <p>workspaceId는 Item·Category와 동일하게 FK 연관 없이 생 id 컬럼으로 둔다.
 */
@Getter
@Entity
@Table(name = "temporary_candidates")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class TemporaryCandidate extends BaseTimeEntity {

    public static final String PENDING = "PENDING";
    public static final String READY_TO_PROMOTE = "READY_TO_PROMOTE";
    public static final String PROMOTED = "PROMOTED";

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long workspaceId;

    @Column(nullable = false, length = 100)
    private String suggestedName;

    @Column(length = 20)
    private String anchorType;

    @Column(length = 100)
    private String normalizedAnchorName;

    @Column(nullable = false)
    private int supportCount;

    @Column(nullable = false, length = 20)
    private String status;

    private Long promotedCategoryId;

    @Builder
    private TemporaryCandidate(Long workspaceId, String suggestedName, String anchorType,
            String normalizedAnchorName, int supportCount, String status) {
        this.workspaceId = workspaceId;
        this.suggestedName = suggestedName;
        this.anchorType = anchorType;
        this.normalizedAnchorName = normalizedAnchorName;
        this.supportCount = supportCount;
        this.status = (status == null || status.isBlank()) ? PENDING : status;
    }

    /** 연결 데이터가 늘어 supportCount가 갱신됐을 때(AI가 계산한 supportCountAfter 반영). */
    public void updateSupportCount(int supportCount) {
        this.supportCount = supportCount;
    }

    /** 승격 확정 — 상태를 PROMOTED로 바꾸고 생성된 정식 카테고리 id를 기록한다. */
    public void promote(Long promotedCategoryId) {
        this.status = PROMOTED;
        this.promotedCategoryId = promotedCategoryId;
    }
}
