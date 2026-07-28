package com.ssafy.woojuin.domain.item.processing;

import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.domain.item.repository.ItemRepository;
import java.util.List;
import java.util.Map;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * 큐 메시지 하나를 처리하는 핵심 로직. 최초 소비({@link ItemQueueConsumer})와 재시도
 * 회수({@link PendingMessageReclaimer})가 공유한다 — ACK 여부는 호출부가 결과를 보고 정한다.
 */
@Slf4j
@Component
public class ItemProcessingDispatcher {

    /** 메시지 처리 결과. 호출부는 이 값으로 ACK/재시도/폐기를 판단한다. */
    public enum Outcome {
        /** 정상 처리됨 → ACK */
        PROCESSED,
        /** 형식이 깨져 재시도해도 소용없음 → ACK 후 폐기 */
        POISON,
        /** 담당 프로세서가 아직 없음(예: 묶음 F 미구현 타입) → pending 유지, 재시도 대상 아님 */
        NO_PROCESSOR,
        /** 처리 중 예외 → pending 유지, 재시도 대상 */
        RETRYABLE
    }

    private final List<ItemProcessor> processors;
    private final ItemRepository itemRepository;

    public ItemProcessingDispatcher(List<ItemProcessor> processors, ItemRepository itemRepository) {
        this.processors = processors;
        this.itemRepository = itemRepository;
    }

    public Outcome handle(Map<String, String> fields) {
        ItemProcessingMessage message;
        try {
            message = ItemProcessingMessage.from(fields);
        } catch (IllegalArgumentException e) {
            log.error("큐 메시지 파싱 실패, 폐기: value={}", fields, e);
            return Outcome.POISON;
        }

        ItemProcessor processor = findProcessor(message);
        if (processor == null) {
            log.warn("타입 {}를 처리할 프로세서 없음, pending 유지: itemId={}",
                    message.type(), message.itemId());
            return Outcome.NO_PROCESSOR;
        }

        try {
            processor.process(message);
            return Outcome.PROCESSED;
        } catch (Exception e) {
            log.error("아이템 처리 실패, 재시도 예정: itemId={}, type={}",
                    message.itemId(), message.type(), e);
            return Outcome.RETRYABLE;
        }
    }

    public ItemProcessor findProcessor(ItemProcessingMessage message) {
        return processors.stream()
                .filter(p -> p.supports(message.type()))
                .findFirst()
                .orElse(null);
    }

    /** 재시도 상한을 넘겨 최종 포기할 때. 사용자에겐 URL만 남고 알림은 생략된다(AGENTS.md 규칙 6). */
    @Transactional
    public void markFailed(Long itemId) {
        Item item = itemRepository.findById(itemId).orElse(null);
        if (item == null) {
            log.warn("FAILED 처리할 아이템이 없음(삭제됨?): itemId={}", itemId);
            return;
        }
        item.markFailed();
        log.warn("재시도 상한 초과로 FAILED 확정: itemId={}", itemId);
    }
}
