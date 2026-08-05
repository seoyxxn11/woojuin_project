package com.ssafy.woojuin.domain.ai.engine.repository;

import com.ssafy.woojuin.domain.ai.engine.entity.CategoryAnchor;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CategoryAnchorRepository extends JpaRepository<CategoryAnchor, Long> {

    /** 승격 카테고리 재사용 매칭용 — 같은 정규화 앵커를 가진 정식 카테고리 앵커. */
    List<CategoryAnchor> findByNormalizedAnchorName(String normalizedAnchorName);
}
