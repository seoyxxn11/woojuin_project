package com.ssafy.woojuin.domain.item.processing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.domain.item.repository.ItemRepository;
import com.ssafy.woojuin.domain.item.entity.ItemType;
import com.ssafy.woojuin.global.common.ItemStatus;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class ItemProcessingDispatcherTest {

    private final ItemRepository itemRepository = mock(ItemRepository.class);

    private ItemProcessingDispatcher dispatcher(ItemProcessor... processors) {
        return new ItemProcessingDispatcher(List.of(processors), itemRepository);
    }

    private ItemProcessor urlProcessor() {
        ItemProcessor p = mock(ItemProcessor.class);
        when(p.supports(ItemType.URL)).thenReturn(true);
        return p;
    }

    private Map<String, String> urlFields() {
        return Map.of("itemId", "1", "workspaceId", "1", "type", "URL");
    }

    @Test
    void 정상_처리되면_PROCESSED() {
        ItemProcessingDispatcher dispatcher = dispatcher(urlProcessor());

        assertThat(dispatcher.handle(urlFields()))
                .isEqualTo(ItemProcessingDispatcher.Outcome.PROCESSED);
    }

    @Test
    void 형식이_깨지면_POISON() {
        ItemProcessingDispatcher dispatcher = dispatcher(urlProcessor());

        assertThat(dispatcher.handle(Map.of("itemId", "abc")))
                .isEqualTo(ItemProcessingDispatcher.Outcome.POISON);
    }

    @Test
    void 담당_프로세서가_없으면_NO_PROCESSOR() {
        ItemProcessingDispatcher dispatcher = dispatcher();   // 아무 프로세서도 없음

        assertThat(dispatcher.handle(urlFields()))
                .isEqualTo(ItemProcessingDispatcher.Outcome.NO_PROCESSOR);
    }

    @Test
    void 처리중_예외가_나면_RETRYABLE() {
        ItemProcessor p = urlProcessor();
        doThrow(new RuntimeException("일시 실패")).when(p).process(any());
        ItemProcessingDispatcher dispatcher = dispatcher(p);

        assertThat(dispatcher.handle(urlFields()))
                .isEqualTo(ItemProcessingDispatcher.Outcome.RETRYABLE);
    }

    @Test
    void markFailed_아이템을_FAILED로_바꾼다() {
        Item item = Item.builder().workspaceId(1L).createdBy(1L).type(ItemType.URL)
                .url("https://example.com").build();
        when(itemRepository.findById(1L)).thenReturn(Optional.of(item));
        ItemProcessingDispatcher dispatcher = dispatcher();

        dispatcher.markFailed(1L);

        assertThat(item.getStatus()).isEqualTo(ItemStatus.FAILED);
    }

    @Test
    void markFailed_아이템이_없어도_예외없이_넘어간다() {
        when(itemRepository.findById(any())).thenReturn(Optional.empty());
        ItemProcessingDispatcher dispatcher = dispatcher();

        dispatcher.markFailed(99L);   // 예외 없이 통과
    }
}
