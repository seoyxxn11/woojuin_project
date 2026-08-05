package com.ssafy.woojuin.domain.ai.engine;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.woojuin.domain.ai.CategoryEngineClient;
import com.ssafy.woojuin.domain.ai.engine.entity.CandidateItemLink;
import com.ssafy.woojuin.domain.ai.engine.entity.CategoryAnchor;
import com.ssafy.woojuin.domain.ai.engine.entity.TemporaryCandidate;
import com.ssafy.woojuin.domain.ai.engine.repository.CandidateAliasRepository;
import com.ssafy.woojuin.domain.ai.engine.repository.CandidateItemLinkRepository;
import com.ssafy.woojuin.domain.ai.engine.repository.CategoryAnchorRepository;
import com.ssafy.woojuin.domain.ai.engine.repository.TemporaryCandidateRepository;
import com.ssafy.woojuin.domain.category.entity.Category;
import com.ssafy.woojuin.domain.category.entity.ItemCategory;
import com.ssafy.woojuin.domain.category.repository.CategoryRepository;
import com.ssafy.woojuin.domain.category.repository.ItemCategoryRepository;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class CategoryEngineActionExecutorTest {

    @Mock CategoryRepository categoryRepository;
    @Mock ItemCategoryRepository itemCategoryRepository;
    @Mock TemporaryCandidateRepository candidateRepository;
    @Mock CandidateItemLinkRepository linkRepository;
    @Mock CandidateAliasRepository aliasRepository;
    @Mock CategoryAnchorRepository categoryAnchorRepository;
    @Mock CategoryEngineSignalStore signalStore;

    @InjectMocks CategoryEngineActionExecutor executor;

    private static CategoryEngineClient.EngineAction action(String type) {
        return new CategoryEngineClient.EngineAction(type, null, null, null, null, null, null, null, null, null, null);
    }

    private static CategoryEngineClient.DecideResult result(List<CategoryEngineClient.EngineAction> actions) {
        var anchor = new CategoryEngineClient.CategoryAnchor("A", "a", "ENTITY", List.of(), List.of(), 0.9);
        var match = new CategoryEngineClient.Match("NONE", null, null);
        return new CategoryEngineClient.DecideResult(10L, 1L, List.of(), false, anchor, match, actions);
    }

    @Test
    void linkFormalCategory_savesOnlyNewLinks() {
        when(itemCategoryRepository.existsByItemIdAndCategoryId(1L, 2L)).thenReturn(false);
        when(itemCategoryRepository.existsByItemIdAndCategoryId(1L, 7L)).thenReturn(true); // 이미 연결됨
        var actions = List.of(
                new CategoryEngineClient.EngineAction("LINK_FORMAL_CATEGORY", 2L, null, null, null, null, null, null, null, null, null),
                new CategoryEngineClient.EngineAction("LINK_FORMAL_CATEGORY", 7L, null, null, null, null, null, null, null, null, null));

        var r = executor.apply(10L, 1L, "t", "s", result(actions));

        assertThat(r.linkedCategoryIds()).containsExactly(2L);  // 7L은 멱등 스킵
        verify(itemCategoryRepository, times(1)).save(any(ItemCategory.class));
    }

    @Test
    void storeSignal_callsSignalStore() {
        var actions = List.of(new CategoryEngineClient.EngineAction(
                "STORE_SIGNAL", null, null, null, "SSAFY", "ENTITY", "SSAFY", List.of("ssafy"), List.of(1L), null, null));

        var r = executor.apply(10L, 1L, "제목", "요약", result(actions));

        assertThat(r.signalStored()).isTrue();
        verify(signalStore, times(1)).store(eq(10L), any(CategoryEngineSignalStore.StoredSignal.class));
    }

    @Test
    void createCandidate_savesCandidateLinksAndDeletesSignal() {
        var saved = TemporaryCandidate.builder().workspaceId(10L).suggestedName("SSAFY")
                .anchorType("ENTITY").normalizedAnchorName("SSAFY").supportCount(2)
                .status(TemporaryCandidate.PENDING).build();
        ReflectionTestUtils.setField(saved, "id", 55L);
        when(candidateRepository.save(any(TemporaryCandidate.class))).thenReturn(saved);
        when(linkRepository.existsByCandidateIdAndItemId(anyLong(), anyLong())).thenReturn(false);
        when(aliasRepository.existsByCandidateIdAndAliasKey(anyLong(), anyString())).thenReturn(false);

        var actions = List.of(new CategoryEngineClient.EngineAction(
                "CREATE_CANDIDATE", null, null, 2, "SSAFY", "ENTITY", "SSAFY", List.of("ssafy"), List.of(1L, 2L), null, null));

        var r = executor.apply(10L, 2L, "t", "s", result(actions));

        assertThat(r.createdCandidateId()).isEqualTo(55L);
        verify(linkRepository, times(2)).save(any(CandidateItemLink.class));  // item 1,2
        verify(signalStore, times(1)).delete(10L, "SSAFY");
    }

    @Test
    void linkCandidate_savesLinkAndUpdatesSupportCount() {
        var candidate = TemporaryCandidate.builder().workspaceId(10L).suggestedName("SSAFY")
                .anchorType("ENTITY").normalizedAnchorName("SSAFY").supportCount(2)
                .status(TemporaryCandidate.PENDING).build();
        ReflectionTestUtils.setField(candidate, "id", 7L);
        when(linkRepository.existsByCandidateIdAndItemId(7L, 3L)).thenReturn(false);
        when(candidateRepository.findById(7L)).thenReturn(Optional.of(candidate));

        var actions = List.of(new CategoryEngineClient.EngineAction(
                "LINK_CANDIDATE", null, 7L, 3, null, null, null, null, null, null, null));

        executor.apply(10L, 3L, "t", "s", result(actions));

        verify(linkRepository, times(1)).save(any(CandidateItemLink.class));
        assertThat(candidate.getSupportCount()).isEqualTo(3);  // supportCountAfter 반영
    }

    @Test
    void promoteCandidate_createsCategoryAnchorAndRelinksItems() {
        var candidate = TemporaryCandidate.builder().workspaceId(10L).suggestedName("SSAFY")
                .anchorType("ENTITY").normalizedAnchorName("SSAFY").supportCount(3)
                .status(TemporaryCandidate.PENDING).build();
        ReflectionTestUtils.setField(candidate, "id", 7L);
        when(candidateRepository.findById(7L)).thenReturn(Optional.of(candidate));
        when(categoryRepository.findByWorkspaceIdAndName(10L, "SSAFY")).thenReturn(Optional.empty());
        var newCategory = Category.builder().workspaceId(10L).name("SSAFY").build();
        ReflectionTestUtils.setField(newCategory, "id", 99L);
        when(categoryRepository.save(any(Category.class))).thenReturn(newCategory);
        when(categoryAnchorRepository.existsById(99L)).thenReturn(false);
        when(linkRepository.findByCandidateId(7L)).thenReturn(List.of(
                CandidateItemLink.builder().candidateId(7L).itemId(1L).build(),
                CandidateItemLink.builder().candidateId(7L).itemId(2L).build()));
        when(itemCategoryRepository.existsByItemIdAndCategoryId(anyLong(), eq(99L))).thenReturn(false);

        var actions = List.of(new CategoryEngineClient.EngineAction(
                "PROMOTE_CANDIDATE", null, 7L, null, null, "ENTITY", null, null, null, "SSAFY", null));

        var r = executor.apply(10L, 3L, "t", "s", result(actions));

        assertThat(r.promotedCategoryId()).isEqualTo(99L);
        assertThat(candidate.getStatus()).isEqualTo(TemporaryCandidate.PROMOTED);
        assertThat(candidate.getPromotedCategoryId()).isEqualTo(99L);
        // 앵커 메타 기록
        ArgumentCaptor<CategoryAnchor> anchorCaptor = ArgumentCaptor.forClass(CategoryAnchor.class);
        verify(categoryAnchorRepository).save(anchorCaptor.capture());
        assertThat(anchorCaptor.getValue().getOrigin()).isEqualTo(CategoryAnchor.AI_PROMOTED);
        assertThat(anchorCaptor.getValue().getNormalizedAnchorName()).isEqualTo("SSAFY");
        // 연결 아이템 2건을 새 카테고리로 재분류
        verify(itemCategoryRepository, times(2)).save(any(ItemCategory.class));
    }

    @Test
    void promoteCandidate_missingCandidate_isNoOp() {
        when(candidateRepository.findById(404L)).thenReturn(Optional.empty());
        var actions = List.of(new CategoryEngineClient.EngineAction(
                "PROMOTE_CANDIDATE", null, 404L, null, null, "ENTITY", null, null, null, "X", null));

        var r = executor.apply(10L, 1L, "t", "s", result(actions));

        assertThat(r.promotedCategoryId()).isNull();
        verify(categoryRepository, never()).save(any(Category.class));
    }
}
