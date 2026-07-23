package com.ssafy.woojuin.domain.item.processing.memo;

import com.ssafy.woojuin.domain.ai.AiAnalysis;
import com.ssafy.woojuin.domain.ai.AiAnalysisRequest;
import com.ssafy.woojuin.domain.ai.AiAnalyzer;
import com.ssafy.woojuin.domain.category.service.CategoryAssignmentService;
import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.domain.item.entity.ItemType;
import com.ssafy.woojuin.domain.item.processing.ItemEnrichment;
import com.ssafy.woojuin.domain.item.processing.ItemEnrichmentWriter;
import com.ssafy.woojuin.domain.item.processing.ItemProcessingMessage;
import com.ssafy.woojuin.domain.item.processing.ItemProcessor;
import com.ssafy.woojuin.domain.item.repository.ItemRepository;
import com.ssafy.woojuin.global.common.ItemStatus;
import java.util.List;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 메모 아이템 가공 오케스트레이터 (묶음 D).
 *
 * <p>MEMO는 {@code ItemService.validate()}에서 이미 content가 필수로 검증돼 저장 시점에
 * 본문이 확보돼 있다. URL의 트랙 B(본문 확보)에 항상 해당하는 상태로 태어나는 셈이라 별도의
 * 성공/실패 분기가 없다 — AI 보강 결과와 무관하게 항상 DONE으로 확정한다.
 *
 * <p><b>트랜잭션 경계</b>: AI 호출은 네트워크 I/O라 트랜잭션 밖에서 하고, DB 반영만
 * {@link ItemEnrichmentWriter}의 짧은 트랜잭션에 맡긴다(커넥션 장기 점유 방지).
 */
@Slf4j
@Component
public class MemoItemProcessor implements ItemProcessor {

    private final ItemRepository itemRepository;
    private final AiAnalyzer aiAnalyzer;
    private final CategoryAssignmentService categoryAssignmentService;
    private final ItemEnrichmentWriter enrichmentWriter;

    public MemoItemProcessor(ItemRepository itemRepository, AiAnalyzer aiAnalyzer,
            CategoryAssignmentService categoryAssignmentService,
            ItemEnrichmentWriter enrichmentWriter) {
        this.itemRepository = itemRepository;
        this.aiAnalyzer = aiAnalyzer;
        this.categoryAssignmentService = categoryAssignmentService;
        this.enrichmentWriter = enrichmentWriter;
    }

    @Override
    public boolean supports(ItemType type) {
        return type == ItemType.MEMO;
    }

    @Override
    public void process(ItemProcessingMessage message) {
        Item item = itemRepository.findById(message.itemId()).orElse(null);
        if (item == null) {
            log.warn("가공할 아이템이 없음(삭제됨?): itemId={}", message.itemId());
            return;
        }
        if (item.getStatus() != ItemStatus.PROCESSING) {
            // at-least-once 큐 특성상 이미 끝난 메시지가 재배달될 수 있다. 값비싼 AI 호출을
            // 반복하지 않도록 여기서 미리 막는다(반영 단계에서 한 번 더 권위 있게 재확인한다).
            log.info("이미 처리된 아이템, 재처리 스킵: itemId={}, status={}", item.getId(), item.getStatus());
            return;
        }

        // 네트워크 단계(트랜잭션 밖): AI 요약·분류. 사용자가 쓴 메모는 이미 확보돼 있어
        // AI 결과와 무관하게 항상 DONE으로 확정한다.
        AiAnalysis analysis = analyzeQuietly(item, item.getContent());

        enrichmentWriter.apply(message.itemId(), ItemEnrichment.builder()
                .summary(analysis.summary())
                .categories(analysis.categories())
                .targetStatus(ItemStatus.DONE)
                .build());
        log.info("메모 가공 완료: itemId={}", message.itemId());
    }

    /**
     * AI 요약·분류를 시도한다. 어떤 실패도 이미 저장된 사용자 메모를 무효화하면 안 되므로
     * 조용히 흡수하고 빈 결과를 돌려준다(UrlItemProcessor.analyzeQuietly와 동일 패턴).
     */
    private AiAnalysis analyzeQuietly(Item item, String text) {
        try {
            List<String> candidates = categoryAssignmentService.candidateNames(item.getWorkspaceId());
            return aiAnalyzer.analyze(new AiAnalysisRequest(item.getTitle(), text, candidates));
        } catch (Exception e) {
            log.warn("AI 보강 실패(무시): itemId={}, cause={}", item.getId(), e.toString());
            return AiAnalysis.empty();
        }
    }
}
