package com.ssafy.woojuin.domain.ai.engine;

import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.domain.item.event.ItemDoneEvent;
import com.ssafy.woojuin.domain.item.repository.ItemRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

/**
 * 자동 인제스트 훅. 아이템 가공이 끝나(DONE/PARTIAL 커밋) {@link ItemDoneEvent}가 나면,
 * 그 아이템을 카테고리 엔진으로 후처리한다(상태조회 → decide → actions 적용).
 *
 * <p>코어 처리기(ItemProcessor)를 건드리지 않고 이벤트로 느슨하게 붙였다 — 엔진 실패가 아이템
 * 가공을 되돌리지 않는다(아이템은 이미 DONE 확정). AFTER_COMMIT + @Async라 커밋된 상태에서
 * 처리 스레드와 분리돼 돈다. {@code woojuin.category-engine.enabled=true}일 때만 등록된다.
 *
 * <p>참고: 엔진이 켜져 있으면 기존 분류(categoryAssignmentService)의 기본 카테고리 위에 엔진의
 * 대상 카테고리/후보/신호가 더해진다(LINK는 멱등). 연동 검증 단계의 동작이다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnProperty(name = "woojuin.category-engine.enabled", havingValue = "true")
public class CategoryEngineItemListener {

    private final CategoryEngineOrchestrator orchestrator;
    private final ItemRepository itemRepository;

    @Async
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void onItemDone(ItemDoneEvent event) {
        try {
            Item item = itemRepository.findById(event.itemId()).orElse(null);
            if (item == null) {
                return;
            }
            String summary = item.getSummary() != null ? item.getSummary() : item.getContent();
            CategoryEngineOrchestrator.ProcessOutcome outcome = orchestrator.process(
                    item.getWorkspaceId(), item.getId(),
                    item.getType() != null ? item.getType().name() : "URL",
                    item.getTitle(), summary);
            if (outcome.applied()) {
                var d = outcome.decision();
                log.info("category-engine 처리 완료: itemId={} match={} actions={}",
                        item.getId(),
                        d.match() != null ? d.match().type() : null,
                        d.actions().stream().map(a -> a.type()).toList());
            } else {
                log.info("category-engine 스킵(AI 실패 폴백): itemId={}", item.getId());
            }
        } catch (Exception e) {
            // 엔진 후처리 실패는 아이템 가공을 되돌리지 않는다(아이템은 이미 DONE).
            log.warn("category-engine 아이템 후처리 실패(무시): itemId={}", event.itemId(), e);
        }
    }
}
