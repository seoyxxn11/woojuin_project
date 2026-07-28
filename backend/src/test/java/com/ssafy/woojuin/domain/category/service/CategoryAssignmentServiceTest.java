package com.ssafy.woojuin.domain.category.service;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.woojuin.domain.category.CategoryDefaults;
import com.ssafy.woojuin.domain.category.entity.Category;
import com.ssafy.woojuin.domain.category.entity.ItemCategory;
import com.ssafy.woojuin.domain.category.repository.CategoryRepository;
import com.ssafy.woojuin.domain.category.repository.ItemCategoryRepository;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class CategoryAssignmentServiceTest {

    @Mock CategoryRepository categoryRepository;
    @Mock ItemCategoryRepository itemCategoryRepository;
    @InjectMocks CategoryAssignmentService service;

    private Category category(long id, String name) {
        Category c = Category.builder().workspaceId(1L).name(name).build();
        ReflectionTestUtils.setField(c, "id", id);
        return c;
    }

    @Test
    void 매칭된_카테고리를_아이템에_연결한다() {
        Category learn = category(10L, "학습·지식");
        when(categoryRepository.findByWorkspaceIdAndNameIn(1L, List.of("학습·지식")))
                .thenReturn(List.of(learn));
        when(itemCategoryRepository.existsByItemIdAndCategoryId(5L, 10L)).thenReturn(false);

        service.assign(5L, 1L, List.of("학습·지식"));

        verify(itemCategoryRepository).save(any(ItemCategory.class));
    }

    @Test
    void 매칭이_없으면_기타로_폴백한다() {
        Category etc = category(99L, CategoryDefaults.ETC);
        when(categoryRepository.findByWorkspaceIdAndNameIn(anyLong(), any()))
                .thenReturn(List.of());
        when(categoryRepository.findByWorkspaceIdAndName(1L, CategoryDefaults.ETC))
                .thenReturn(Optional.of(etc));
        when(itemCategoryRepository.existsByItemIdAndCategoryId(5L, 99L)).thenReturn(false);

        service.assign(5L, 1L, List.of("없는카테고리"));

        verify(itemCategoryRepository).save(any(ItemCategory.class));
    }

    @Test
    void AI가_빈_결과여도_기타로_폴백한다() {
        Category etc = category(99L, CategoryDefaults.ETC);
        when(categoryRepository.findByWorkspaceIdAndName(1L, CategoryDefaults.ETC))
                .thenReturn(Optional.of(etc));
        when(itemCategoryRepository.existsByItemIdAndCategoryId(5L, 99L)).thenReturn(false);

        service.assign(5L, 1L, List.of());   // AI 미분류

        verify(itemCategoryRepository).save(any(ItemCategory.class));
        // 이름 목록이 비면 조회 자체를 생략한다
        verify(categoryRepository, never()).findByWorkspaceIdAndNameIn(anyLong(), any());
    }

    @Test
    void 기타조차_없으면_아무것도_연결하지_않는다() {
        when(categoryRepository.findByWorkspaceIdAndName(1L, CategoryDefaults.ETC))
                .thenReturn(Optional.empty());

        service.assign(5L, 1L, List.of());   // 시드 안 된 옛 워크스페이스

        verify(itemCategoryRepository, never()).save(any());
    }

    @Test
    void 이미_연결되어_있으면_중복_저장하지_않는다() {
        Category learn = category(10L, "학습·지식");
        when(categoryRepository.findByWorkspaceIdAndNameIn(1L, List.of("학습·지식")))
                .thenReturn(List.of(learn));
        when(itemCategoryRepository.existsByItemIdAndCategoryId(5L, 10L)).thenReturn(true);

        service.assign(5L, 1L, List.of("학습·지식"));

        verify(itemCategoryRepository, never()).save(any());
    }
}
