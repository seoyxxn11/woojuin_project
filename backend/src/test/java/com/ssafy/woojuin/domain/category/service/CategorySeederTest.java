package com.ssafy.woojuin.domain.category.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.woojuin.domain.category.CategoryDefaults;
import com.ssafy.woojuin.domain.category.entity.Category;
import com.ssafy.woojuin.domain.category.repository.CategoryRepository;
import com.ssafy.woojuin.domain.workspace.event.WorkspaceCreatedEvent;
import java.util.Map;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class CategorySeederTest {

    @Mock CategoryRepository categoryRepository;
    @InjectMocks CategorySeeder seeder;

    @Test
    void 워크스페이스_생성시_기본_카테고리를_시드한다() {
        when(categoryRepository.existsByWorkspaceId(1L)).thenReturn(false);

        seeder.seedDefaults(new WorkspaceCreatedEvent(1L));

        verify(categoryRepository, times(CategoryDefaults.NAMES.size())).save(org.mockito.ArgumentMatchers.any(Category.class));
    }

    @Test
    void 시드시_별자리는_팔레트_순환색_기타는_white가_배정된다() {
        when(categoryRepository.existsByWorkspaceId(1L)).thenReturn(false);
        when(categoryRepository.save(org.mockito.ArgumentMatchers.any(Category.class)))
                .thenAnswer(inv -> inv.getArgument(0));
        ArgumentCaptor<Category> captor = ArgumentCaptor.forClass(Category.class);

        seeder.seedDefaults(new WorkspaceCreatedEvent(1L));

        verify(categoryRepository, times(CategoryDefaults.NAMES.size())).save(captor.capture());
        Map<String, String> colorByName = captor.getAllValues().stream()
                .collect(Collectors.toMap(Category::getName, Category::getColor));
        assertThat(colorByName.get("생활·할 일")).isEqualTo("#C9B8FF");   // ordinal 0 vivid lavender
        assertThat(colorByName.get("음식·맛집")).isEqualTo("#F2D96B");   // ordinal 4 vivid yellow
        assertThat(colorByName.get("쇼핑·제품")).isEqualTo("#D2CAED");   // ordinal 5 muted lavender
        assertThat(colorByName.get("아이디어·영감")).isEqualTo("#D0C48D"); // ordinal 9 muted yellow
        assertThat(colorByName.get(CategoryDefaults.ETC)).isEqualTo("#F5F1E8"); // 기타 = white
    }

    @Test
    void 이미_카테고리가_있으면_시드하지_않는다() {
        when(categoryRepository.existsByWorkspaceId(1L)).thenReturn(true);

        seeder.seedDefaults(new WorkspaceCreatedEvent(1L));

        verify(categoryRepository, never()).save(org.mockito.ArgumentMatchers.any());
    }
}
