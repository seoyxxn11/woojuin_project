package com.ssafy.woojuin.domain.category.service;

import com.ssafy.woojuin.domain.category.CategoryDefaults;
import com.ssafy.woojuin.domain.category.entity.Category;
import com.ssafy.woojuin.domain.category.entity.ItemCategory;
import com.ssafy.woojuin.domain.category.repository.CategoryRepository;
import com.ssafy.woojuin.domain.category.repository.ItemCategoryRepository;
import java.util.List;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

/**
 * AI가 분류한 카테고리 이름들을 아이템에 연결한다. 이름은 그 워크스페이스의 category_id로
 * 매핑하고, 하나도 매칭되지 않으면 "기타"로 폴백해 <b>모든 아이템이 최소 한 카테고리에</b>
 * 속하도록 한다.
 *
 * <p>트랜잭션 경계는 이 메서드를 호출하는 가공 파이프라인이 갖는다(별도 @Transactional을
 * 걸지 않는다) — 미리보기·본문·카테고리 저장이 한 트랜잭션에서 함께 커밋되게 하려는 것.
 */
@Slf4j
@Service
public class CategoryAssignmentService {

    private final CategoryRepository categoryRepository;
    private final ItemCategoryRepository itemCategoryRepository;

    public CategoryAssignmentService(CategoryRepository categoryRepository,
            ItemCategoryRepository itemCategoryRepository) {
        this.categoryRepository = categoryRepository;
        this.itemCategoryRepository = itemCategoryRepository;
    }

    public void assign(Long itemId, Long workspaceId, List<String> categoryNames) {
        List<Category> matched = categoryNames.isEmpty()
                ? List.of()
                : categoryRepository.findByWorkspaceIdAndNameIn(workspaceId, categoryNames);

        if (matched.isEmpty()) {
            // 매칭 실패(AI 미분류/이름 불일치) → "기타"로 폴백. 그것마저 없으면(시드 안 된
            // 옛 워크스페이스) 연결할 카테고리가 없어 그냥 넘어간다.
            matched = categoryRepository.findByWorkspaceIdAndName(workspaceId, CategoryDefaults.ETC)
                    .map(List::of)
                    .orElseGet(List::of);
        }

        for (Category category : matched) {
            if (!itemCategoryRepository.existsByItemIdAndCategoryId(itemId, category.getId())) {
                itemCategoryRepository.save(
                        ItemCategory.builder().itemId(itemId).categoryId(category.getId()).build());
            }
        }
        log.debug("카테고리 연결: itemId={}, categories={}", itemId, matched.stream().map(Category::getName).toList());
    }

    /** AI에 넘길 후보 목록(그 워크스페이스의 현재 카테고리 이름). */
    public List<String> candidateNames(Long workspaceId) {
        return categoryRepository.findByWorkspaceId(workspaceId).stream()
                .map(Category::getName)
                .toList();
    }
}
