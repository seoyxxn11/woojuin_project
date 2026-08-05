package com.ssafy.woojuin.domain.ai.engine.entity;

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
 * 후보 ↔ 아이템 연결. supportCount 산출 근거이며 승격 시 이 아이템들을 새 카테고리로 재분류한다.
 * candidateId/itemId는 생 id 컬럼(기존 패턴).
 */
@Getter
@Entity
@Table(name = "candidate_item_links",
        uniqueConstraints = @UniqueConstraint(columnNames = {"candidate_id", "item_id"}))
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class CandidateItemLink {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long candidateId;

    @Column(nullable = false)
    private Long itemId;

    @Builder
    private CandidateItemLink(Long candidateId, Long itemId) {
        this.candidateId = candidateId;
        this.itemId = itemId;
    }
}
