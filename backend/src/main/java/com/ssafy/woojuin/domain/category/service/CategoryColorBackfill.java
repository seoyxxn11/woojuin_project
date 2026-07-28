package com.ssafy.woojuin.domain.category.service;

import com.ssafy.woojuin.domain.category.CategoryColors;
import com.ssafy.woojuin.domain.category.CategoryDefaults;
import com.ssafy.woojuin.domain.category.entity.Category;
import com.ssafy.woojuin.domain.category.repository.CategoryRepository;
import java.util.Comparator;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * color 컬럼 도입 이전에 만들어진 카테고리(color=null)를 기동 시 한 번 채운다.
 *
 * <p>이 프로젝트는 ddl-auto=update만 쓰고 별도 마이그레이션 도구가 없어, color를
 * NOT NULL로 넣으면 기존 데이터가 있는 환경에서 기동이 깨진다(사용자 avatar_color 전례).
 * 그래서 nullable로 추가한 뒤 여기서 자가치유한다 — 워크스페이스별로 id 순으로 훑어
 * 시더와 같은 규칙(별자리 순환 팔레트, 기타=white)으로 배정한다. 이미 채워진 색은
 * 건드리지 않으므로 재기동해도 안전(idempotent)하다.
 */
@Slf4j
@Component
public class CategoryColorBackfill {

    private final CategoryRepository categoryRepository;

    public CategoryColorBackfill(CategoryRepository categoryRepository) {
        this.categoryRepository = categoryRepository;
    }

    @EventListener(ApplicationReadyEvent.class)
    @Transactional
    public void backfill() {
        Set<Long> workspaceIds = categoryRepository.findByColorIsNull().stream()
                .map(Category::getWorkspaceId)
                .collect(Collectors.toSet());
        if (workspaceIds.isEmpty()) {
            return;
        }

        int fixed = 0;
        for (Long workspaceId : workspaceIds) {
            List<Category> ordered = categoryRepository.findByWorkspaceId(workspaceId).stream()
                    .sorted(Comparator.comparing(Category::getId))
                    .toList();
            int ordinal = 0;
            for (Category category : ordered) {
                boolean isEtc = CategoryDefaults.ETC.equals(category.getName());
                if (category.getColor() == null) {
                    category.applyColor(isEtc ? CategoryColors.UNCATEGORIZED : CategoryColors.forOrdinal(ordinal));
                    fixed++;
                }
                if (!isEtc) {
                    ordinal++;
                }
            }
        }
        log.info("카테고리 색상 백필 완료: {}개 워크스페이스, {}건", workspaceIds.size(), fixed);
    }
}
