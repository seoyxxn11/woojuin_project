package com.ssafy.woojuin.domain.category.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.woojuin.domain.category.CategoryDefaults;
import com.ssafy.woojuin.domain.category.entity.Category;
import com.ssafy.woojuin.domain.category.repository.CategoryRepository;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class CategoryColorBackfillTest {

    @Mock CategoryRepository categoryRepository;
    @InjectMocks CategoryColorBackfill backfill;

    private Category cat(long id, String name) {
        Category c = Category.builder().workspaceId(1L).name(name).build();   // color=null
        ReflectionTestUtils.setField(c, "id", id);
        return c;
    }

    @Test
    void color가_null인_카테고리를_순환색과_기타white로_채운다() {
        Category a = cat(1L, "생활·할 일");
        Category b = cat(2L, "학습·지식");
        Category etc = cat(3L, CategoryDefaults.ETC);
        when(categoryRepository.findByColorIsNull()).thenReturn(List.of(a, b, etc));
        when(categoryRepository.findByWorkspaceId(1L)).thenReturn(List.of(a, b, etc));

        backfill.backfill();

        assertThat(a.getColor()).isEqualTo("#C9B8FF");   // ordinal 0 (lavender)
        assertThat(b.getColor()).isEqualTo("#8FB4FF");   // ordinal 1 (blue)
        assertThat(etc.getColor()).isEqualTo("#F5F1E8"); // 기타 = white
    }

    @Test
    void 채울_대상이_없으면_아무것도_안한다() {
        when(categoryRepository.findByColorIsNull()).thenReturn(List.of());

        backfill.backfill();

        verify(categoryRepository, never()).findByWorkspaceId(any());
    }
}
