package com.ssafy.woojuin.domain.ai.engine.repository;

import com.ssafy.woojuin.domain.ai.engine.entity.TemporaryCandidate;
import java.util.Collection;
import java.util.List;
import org.springframework.data.domain.Limit;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TemporaryCandidateRepository extends JpaRepository<TemporaryCandidate, Long> {

    /** 앵커 Top-K 후보 shortlist 구성용 — 같은 정규화 앵커의 활성 후보. */
    List<TemporaryCandidate> findByWorkspaceIdAndNormalizedAnchorName(
            Long workspaceId, String normalizedAnchorName);

    /** decide 요청의 후보 shortlist — 워크스페이스의 활성 후보(PENDING/READY). 상한으로 자른다. */
    List<TemporaryCandidate> findByWorkspaceIdAndStatusIn(
            Long workspaceId, Collection<String> statuses, Limit limit);
}
