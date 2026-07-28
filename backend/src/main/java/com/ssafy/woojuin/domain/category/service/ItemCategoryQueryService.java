package com.ssafy.woojuin.domain.category.service;

import com.ssafy.woojuin.domain.category.dto.CategoryResponse;
import com.ssafy.woojuin.domain.category.entity.Category;
import com.ssafy.woojuin.domain.category.entity.ItemCategory;
import com.ssafy.woojuin.domain.category.repository.CategoryRepository;
import com.ssafy.woojuin.domain.category.repository.ItemCategoryRepository;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 아이템에 연결된 카테고리를 읽어 응답에 싣기 위한 조회 전용 서비스. 목록 응답의 N+1을
 * 피하려고 여러 아이템의 카테고리를 두 번의 쿼리(연결 조회 + 카테고리 조회)로 배치 처리한다.
 */
@Service
public class ItemCategoryQueryService {

    private final ItemCategoryRepository itemCategoryRepository;
    private final CategoryRepository categoryRepository;

    public ItemCategoryQueryService(ItemCategoryRepository itemCategoryRepository,
            CategoryRepository categoryRepository) {
        this.itemCategoryRepository = itemCategoryRepository;
        this.categoryRepository = categoryRepository;
    }

    @Transactional(readOnly = true)
    public Map<Long, List<CategoryResponse>> categoriesByItemIds(Collection<Long> itemIds) {
        if (itemIds.isEmpty()) {
            return Map.of();
        }
        List<ItemCategory> links = itemCategoryRepository.findByItemIdIn(itemIds);
        if (links.isEmpty()) {
            return Map.of();
        }
        Set<Long> categoryIds = links.stream().map(ItemCategory::getCategoryId).collect(Collectors.toSet());
        Map<Long, Category> categoryById = categoryRepository.findAllById(categoryIds).stream()
                .collect(Collectors.toMap(Category::getId, category -> category));

        Map<Long, List<CategoryResponse>> byItem = new HashMap<>();
        for (ItemCategory link : links) {
            Category category = categoryById.get(link.getCategoryId());
            if (category != null) {   // 조회 사이에 삭제됐으면 건너뛴다
                byItem.computeIfAbsent(link.getItemId(), k -> new ArrayList<>())
                        .add(CategoryResponse.from(category));
            }
        }
        return byItem;
    }

    @Transactional(readOnly = true)
    public List<CategoryResponse> categoriesOf(Long itemId) {
        return categoriesByItemIds(List.of(itemId)).getOrDefault(itemId, List.of());
    }

    /** 카테고리 필터용 — 그 카테고리들 중 하나라도(OR) 연결된 아이템 id 목록(없으면 빈 리스트). */
    @Transactional(readOnly = true)
    public List<Long> itemIdsInCategories(Collection<Long> categoryIds) {
        return itemCategoryRepository.findItemIdsByCategoryIdIn(categoryIds);
    }
}
