package com.ssafy.woojuin.domain.category.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.ssafy.woojuin.domain.category.dto.CategoryResponse;
import com.ssafy.woojuin.domain.category.entity.Category;
import com.ssafy.woojuin.domain.category.entity.ItemCategory;
import com.ssafy.woojuin.domain.category.repository.CategoryRepository;
import com.ssafy.woojuin.domain.category.repository.ItemCategoryRepository;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class ItemCategoryQueryServiceTest {

    @Mock ItemCategoryRepository itemCategoryRepository;
    @Mock CategoryRepository categoryRepository;
    @InjectMocks ItemCategoryQueryService service;

    private Category category(long id, String name) {
        Category c = Category.builder().workspaceId(1L).name(name).build();
        ReflectionTestUtils.setField(c, "id", id);
        return c;
    }

    private ItemCategory link(long itemId, long categoryId) {
        return ItemCategory.builder().itemId(itemId).categoryId(categoryId).build();
    }

    @Test
    void 아이템별로_카테고리를_묶는다() {
        when(itemCategoryRepository.findByItemIdIn(List.of(1L, 2L)))
                .thenReturn(List.of(link(1L, 10L), link(1L, 11L), link(2L, 10L)));
        when(categoryRepository.findAllById(java.util.Set.of(10L, 11L)))
                .thenReturn(List.of(category(10L, "학습·지식"), category(11L, "여행·장소")));

        Map<Long, List<CategoryResponse>> result = service.categoriesByItemIds(List.of(1L, 2L));

        assertThat(result.get(1L)).extracting(CategoryResponse::name)
                .containsExactlyInAnyOrder("학습·지식", "여행·장소");
        assertThat(result.get(2L)).extracting(CategoryResponse::name).containsExactly("학습·지식");
    }

    @Test
    void 입력이_비면_빈_맵을_반환한다() {
        assertThat(service.categoriesByItemIds(List.of())).isEmpty();
    }

    @Test
    void 조회_사이_삭제된_카테고리는_건너뛴다() {
        when(itemCategoryRepository.findByItemIdIn(List.of(1L)))
                .thenReturn(List.of(link(1L, 10L), link(1L, 99L)));
        when(categoryRepository.findAllById(java.util.Set.of(10L, 99L)))
                .thenReturn(List.of(category(10L, "학습·지식")));   // 99L은 사라짐

        Map<Long, List<CategoryResponse>> result = service.categoriesByItemIds(List.of(1L));

        assertThat(result.get(1L)).extracting(CategoryResponse::name).containsExactly("학습·지식");
    }
}
