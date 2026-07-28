package com.ssafy.woojuin.domain.category.repository;

import com.ssafy.woojuin.domain.category.entity.Category;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CategoryRepository extends JpaRepository<Category, Long> {

    /** AI에 넘길 후보 목록(그 워크스페이스에 현재 존재하는 카테고리). */
    List<Category> findByWorkspaceId(Long workspaceId);

    /** AI가 돌려준 이름들을 그 워크스페이스의 카테고리로 매핑. */
    List<Category> findByWorkspaceIdAndNameIn(Long workspaceId, Collection<String> names);

    /** "기타" 폴백 조회 등. */
    Optional<Category> findByWorkspaceIdAndName(Long workspaceId, String name);

    boolean existsByWorkspaceId(Long workspaceId);

    /** 색상 백필 대상(color 미설정 카테고리) 조회. */
    List<Category> findByColorIsNull();

    /** 같은 워크스페이스 안 이름 중복 검사. */
    boolean existsByWorkspaceIdAndName(Long workspaceId, String name);
}
