package com.ssafy.woojuin.domain.ai.engine.repository;

import com.ssafy.woojuin.domain.ai.engine.entity.CandidateAlias;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CandidateAliasRepository extends JpaRepository<CandidateAlias, Long> {

    List<CandidateAlias> findByCandidateId(Long candidateId);

    boolean existsByCandidateIdAndAliasKey(Long candidateId, String aliasKey);
}
