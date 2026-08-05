package com.ssafy.woojuin.domain.ai.engine.repository;

import com.ssafy.woojuin.domain.ai.engine.entity.CandidateItemLink;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CandidateItemLinkRepository extends JpaRepository<CandidateItemLink, Long> {

    List<CandidateItemLink> findByCandidateId(Long candidateId);

    boolean existsByCandidateIdAndItemId(Long candidateId, Long itemId);
}
