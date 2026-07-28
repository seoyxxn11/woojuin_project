package com.ssafy.woojuin.domain.item.processing.memo;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.ssafy.woojuin.domain.ai.AiAnalysis;
import com.ssafy.woojuin.domain.ai.AiAnalyzer;
import com.ssafy.woojuin.domain.category.service.CategoryAssignmentService;
import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.domain.item.entity.ItemType;
import com.ssafy.woojuin.domain.item.processing.ItemProcessingMessage;
import com.ssafy.woojuin.domain.item.repository.ItemRepository;
import com.ssafy.woojuin.global.common.ItemStatus;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class MemoItemProcessorTest {

    @Mock ItemRepository itemRepository;
    @Mock AiAnalyzer aiAnalyzer;
    @Mock CategoryAssignmentService categoryAssignmentService;

    MemoItemProcessor processor;

    private Item memoItem() {
        Item item = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.MEMO)
                .content("사용자가 쓴 메모").build();
        when(itemRepository.findById(any())).thenReturn(Optional.of(item));
        return item;
    }

    private ItemProcessingMessage message() {
        return new ItemProcessingMessage(1L, 1L, ItemType.MEMO);
    }

    @Test
    void 아이템이_사라졌으면_조용히_반환한다() {
        processor = new MemoItemProcessor(itemRepository, aiAnalyzer, categoryAssignmentService);
        when(itemRepository.findById(any())).thenReturn(Optional.empty());

        processor.process(message());

        verifyNoInteractions(aiAnalyzer, categoryAssignmentService);
    }

    @Test
    void AI가_요약과_카테고리를_주면_저장하고_DONE() {
        processor = new MemoItemProcessor(itemRepository, aiAnalyzer, categoryAssignmentService);
        Item item = memoItem();
        when(aiAnalyzer.analyze(any())).thenReturn(new AiAnalysis("요약문", List.of("생활·할 일")));

        processor.process(message());

        assertThat(item.getStatus()).isEqualTo(ItemStatus.DONE);
        assertThat(item.getSummary()).isEqualTo("요약문");
        verify(categoryAssignmentService).assign(eq(item.getId()), eq(1L), eq(List.of("생활·할 일")));
    }

    @Test
    void AI가_예외를_던져도_DONE_유지하고_summary는_비워둔다() {
        processor = new MemoItemProcessor(itemRepository, aiAnalyzer, categoryAssignmentService);
        Item item = memoItem();
        when(aiAnalyzer.analyze(any())).thenThrow(new RuntimeException("AI 서버 장애"));

        processor.process(message());

        assertThat(item.getStatus()).isEqualTo(ItemStatus.DONE);
        assertThat(item.getSummary()).isNull();
    }

    @Test
    void AI가_empty를_반환해도_PARTIAL이_아니라_DONE이다() {
        processor = new MemoItemProcessor(itemRepository, aiAnalyzer, categoryAssignmentService);
        Item item = memoItem();
        when(aiAnalyzer.analyze(any())).thenReturn(AiAnalysis.empty());

        processor.process(message());

        assertThat(item.getStatus()).isEqualTo(ItemStatus.DONE);
    }

    @Test
    void 이미_처리된_아이템은_재처리하지_않는다() {
        processor = new MemoItemProcessor(itemRepository, aiAnalyzer, categoryAssignmentService);
        Item item = memoItem();
        item.markDone();   // at-least-once 큐 재배달 시나리오 시뮬레이션

        processor.process(message());

        verifyNoInteractions(aiAnalyzer, categoryAssignmentService);
    }
}
