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
 * 후보 별칭(정규화 키). 같은 대상의 다른 표기를 앵커 매칭에 쓴다. candidateId는 생 id 컬럼.
 */
@Getter
@Entity
@Table(name = "candidate_aliases",
        uniqueConstraints = @UniqueConstraint(columnNames = {"candidate_id", "alias_key"}))
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class CandidateAlias {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long candidateId;

    @Column(nullable = false, length = 100)
    private String aliasKey;

    @Builder
    private CandidateAlias(Long candidateId, String aliasKey) {
        this.candidateId = candidateId;
        this.aliasKey = aliasKey;
    }
}
