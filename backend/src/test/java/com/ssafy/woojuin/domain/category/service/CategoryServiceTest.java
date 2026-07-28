package com.ssafy.woojuin.domain.category.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.woojuin.domain.category.CategoryDefaults;
import com.ssafy.woojuin.domain.category.dto.CategoryResponse;
import com.ssafy.woojuin.domain.category.entity.Category;
import com.ssafy.woojuin.domain.category.exception.CategoryNotFoundException;
import com.ssafy.woojuin.domain.category.repository.CategoryRepository;
import com.ssafy.woojuin.domain.category.repository.ItemCategoryRepository;
import com.ssafy.woojuin.domain.workspace.entity.WorkspaceMember;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceMemberRequiredException;
import com.ssafy.woojuin.domain.workspace.repository.WorkspaceMemberRepository;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class CategoryServiceTest {

    @Mock CategoryRepository categoryRepository;
    @Mock ItemCategoryRepository itemCategoryRepository;
    @Mock WorkspaceMemberRepository workspaceMemberRepository;
    @InjectMocks CategoryService service;

    private Category category(long id, long workspaceId, String name) {
        Category c = Category.builder().workspaceId(workspaceId).name(name).build();
        ReflectionTestUtils.setField(c, "id", id);
        return c;
    }

    private void memberOf(long workspaceId) {
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(workspaceId, 1L))
                .thenReturn(Optional.of(org.mockito.Mockito.mock(WorkspaceMember.class)));
    }

    @Test
    void 멤버가_아니면_거부한다() {
        when(workspaceMemberRepository.findByWorkspaceIdAndUserId(1L, 1L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.list(1L, 1L, false))
                .isInstanceOf(WorkspaceMemberRequiredException.class);
    }

    @Test
    void hasItems면_활성_아이템_있는_카테고리만_반환한다() {
        memberOf(1L);
        Category withItems = category(10L, 1L, "학습·지식");
        Category empty = category(11L, 1L, "여행·장소");
        when(categoryRepository.findByWorkspaceId(1L)).thenReturn(java.util.List.of(withItems, empty));
        when(itemCategoryRepository.findCategoryIdsWithActiveItems(1L)).thenReturn(java.util.List.of(10L));

        java.util.List<CategoryResponse> result = service.list(1L, 1L, true);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).name()).isEqualTo("학습·지식");
    }

    @Test
    void hasItems_false면_빈_카테고리도_전부_반환한다() {
        memberOf(1L);
        when(categoryRepository.findByWorkspaceId(1L))
                .thenReturn(java.util.List.of(category(10L, 1L, "학습·지식"), category(11L, 1L, "여행·장소")));

        java.util.List<CategoryResponse> result = service.list(1L, 1L, false);

        assertThat(result).hasSize(2);
    }

    @Test
    void 카테고리를_생성한다() {
        memberOf(1L);
        when(categoryRepository.existsByWorkspaceIdAndName(1L, "새카테고리")).thenReturn(false);
        when(categoryRepository.save(any(Category.class))).thenAnswer(inv -> {
            Category c = inv.getArgument(0);
            ReflectionTestUtils.setField(c, "id", 100L);
            return c;
        });

        CategoryResponse response = service.create(1L, 1L, "새카테고리");

        assertThat(response.name()).isEqualTo("새카테고리");
        // 기존 별자리가 없으니 팔레트 첫 색(lavender)이 자동 배정된다.
        assertThat(response.color()).isEqualTo("#C9B8FF");
    }

    @Test
    void 이름이_중복이면_생성을_거부한다() {
        memberOf(1L);
        when(categoryRepository.existsByWorkspaceIdAndName(1L, "학습·지식")).thenReturn(true);

        assertThatThrownBy(() -> service.create(1L, 1L, "학습·지식"))
                .isInstanceOf(IllegalArgumentException.class);
        verify(categoryRepository, never()).save(any());
    }

    @Test
    void 기타는_수정할_수_없다() {
        memberOf(1L);
        when(categoryRepository.findById(9L)).thenReturn(Optional.of(category(9L, 1L, CategoryDefaults.ETC)));

        assertThatThrownBy(() -> service.rename(1L, 1L, 9L, "기타2"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void 카테고리_이름을_수정한다() {
        memberOf(1L);
        Category c = category(5L, 1L, "옛이름");
        when(categoryRepository.findById(5L)).thenReturn(Optional.of(c));
        when(categoryRepository.existsByWorkspaceIdAndName(1L, "새이름")).thenReturn(false);

        CategoryResponse response = service.rename(1L, 1L, 5L, "새이름");

        assertThat(response.name()).isEqualTo("새이름");
        assertThat(c.getName()).isEqualTo("새이름");
    }

    @Test
    void 다른_워크스페이스_카테고리는_접근할_수_없다() {
        memberOf(1L);
        when(categoryRepository.findById(5L)).thenReturn(Optional.of(category(5L, 999L, "남의것")));

        assertThatThrownBy(() -> service.rename(1L, 1L, 5L, "새이름"))
                .isInstanceOf(CategoryNotFoundException.class);
    }

    @Test
    void 기타는_삭제할_수_없다() {
        memberOf(1L);
        when(categoryRepository.findById(9L)).thenReturn(Optional.of(category(9L, 1L, CategoryDefaults.ETC)));

        assertThatThrownBy(() -> service.delete(1L, 1L, 9L))
                .isInstanceOf(IllegalArgumentException.class);
        verify(categoryRepository, never()).delete(any());
    }

    @Test
    void 삭제하면_아이템_연결을_먼저_끊고_삭제한다() {
        memberOf(1L);
        Category c = category(5L, 1L, "지울것");
        when(categoryRepository.findById(5L)).thenReturn(Optional.of(c));

        service.delete(1L, 1L, 5L);

        verify(itemCategoryRepository).deleteByCategoryId(5L);
        verify(categoryRepository).delete(c);
    }
}
