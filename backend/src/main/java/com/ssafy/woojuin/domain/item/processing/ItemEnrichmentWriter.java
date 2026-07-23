package com.ssafy.woojuin.domain.item.processing;

import com.ssafy.woojuin.domain.category.service.CategoryAssignmentService;
import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.domain.item.repository.ItemRepository;
import com.ssafy.woojuin.global.common.ItemStatus;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * 네트워크 가공 결과({@link ItemEnrichment})를 <b>한 번의 짧은 트랜잭션</b>에서 아이템에 반영한다.
 *
 * <p><b>왜 프로세서와 분리된 별도 빈인가</b><br>
 * 프로세서의 {@code process()}는 HTML fetch·OCR·AI 호출 같은 수 초짜리 네트워크 I/O를 한다.
 * 이를 {@code @Transactional}로 감싸면 그 시간 내내 DB 커넥션과 아이템 행 락을 붙잡아,
 * {@code ItemService.createFromImage}가 경고한 것과 같은 커넥션 풀 고갈을 부른다. 그래서
 * 네트워크는 트랜잭션 밖에서 끝내고, DB 반영만 이 빈의 {@code @Transactional} 메서드로 분리한다.
 * ({@code @Transactional}은 같은 클래스 안 자기호출로는 프록시가 걸리지 않아 별도 빈이 필요하다.)
 *
 * <p>반영 직전 아이템을 다시 로드해 상태를 재확인한다 — 프리체크와 이 시점 사이에 다른
 * 소비자(at-least-once 재배달/다중 인스턴스)가 먼저 끝냈을 수 있다. PROCESSING이 아니면
 * 남의 결과를 덮어쓰지 않도록 스킵한다.
 */
@Slf4j
@Component
public class ItemEnrichmentWriter {

    private final ItemRepository itemRepository;
    private final CategoryAssignmentService categoryAssignmentService;

    public ItemEnrichmentWriter(ItemRepository itemRepository,
            CategoryAssignmentService categoryAssignmentService) {
        this.itemRepository = itemRepository;
        this.categoryAssignmentService = categoryAssignmentService;
    }

    @Transactional
    public void apply(Long itemId, ItemEnrichment enrichment) {
        Item item = itemRepository.findById(itemId).orElse(null);
        if (item == null) {
            log.warn("반영할 아이템이 없음(삭제됨?): itemId={}", itemId);
            return;
        }
        if (item.getStatus() != ItemStatus.PROCESSING) {
            log.info("이미 처리된 아이템, 반영 스킵: itemId={}, status={}", itemId, item.getStatus());
            return;
        }

        item.applyPreview(enrichment.previewTitle(), enrichment.previewThumbnailUrl(),
                enrichment.previewDescription());
        item.applyContent(enrichment.content());
        item.applySummary(enrichment.summary());
        categoryAssignmentService.assign(item.getId(), item.getWorkspaceId(), enrichment.categories());
        applyStatus(item, enrichment.targetStatus());
        log.info("아이템 가공 반영 완료: itemId={}, status={}", itemId, item.getStatus());
    }

    private void applyStatus(Item item, ItemStatus target) {
        switch (target) {
            case DONE -> item.markDone();
            case PARTIAL -> item.markPartial();
            case FAILED -> item.markFailed();
            default -> throw new IllegalArgumentException("가공 반영에 쓸 수 없는 목표 상태: " + target);
        }
    }
}
