package com.ssafy.woojuin.domain.category.service;

import com.ssafy.woojuin.domain.category.CategoryColors;
import com.ssafy.woojuin.domain.category.CategoryDefaults;
import com.ssafy.woojuin.domain.category.entity.Category;
import com.ssafy.woojuin.domain.category.repository.CategoryRepository;
import com.ssafy.woojuin.domain.workspace.event.WorkspaceCreatedEvent;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

/**
 * 워크스페이스 생성 시 기본 카테고리 11개를 시드한다.
 *
 * <p>동기 @EventListener라 워크스페이스 생성 트랜잭션 안에서 실행된다 — 시드가 실패하면
 * 워크스페이스 생성도 함께 롤백돼 "카테고리 없는 워크스페이스"가 생기지 않는다.
 */
@Slf4j
@Component
public class CategorySeeder {

    private final CategoryRepository categoryRepository;

    public CategorySeeder(CategoryRepository categoryRepository) {
        this.categoryRepository = categoryRepository;
    }

    @EventListener
    public void seedDefaults(WorkspaceCreatedEvent event) {
        Long workspaceId = event.workspaceId();
        // 재발행·중복 방지. 이미 카테고리가 있으면 건드리지 않는다.
        if (categoryRepository.existsByWorkspaceId(workspaceId)) {
            return;
        }
        // 별자리 팔레트를 순환 배정하고 "기타"만 미분류 색(white)으로 시드한다.
        int ordinal = 0;
        for (String name : CategoryDefaults.NAMES) {
            String color = CategoryDefaults.ETC.equals(name)
                    ? CategoryColors.UNCATEGORIZED
                    : CategoryColors.forOrdinal(ordinal++);
            categoryRepository.save(
                    Category.builder().workspaceId(workspaceId).name(name).color(color).build());
        }
        log.info("기본 카테고리 {}개 시드 완료: workspaceId={}", CategoryDefaults.NAMES.size(), workspaceId);
    }
}
