package com.ssafy.woojuin.domain.ai.engine;

import com.ssafy.woojuin.domain.ai.CategoryEngineClient;
import com.ssafy.woojuin.domain.item.entity.Item;
import com.ssafy.woojuin.domain.item.repository.ItemRepository;
import com.ssafy.woojuin.global.common.ApiResponse;
import com.ssafy.woojuin.global.security.aop.AuthenticatedUser;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

/**
 * 카테고리 엔진 수동 테스트 엔드포인트. 이미 저장된 아이템 하나를 골라 상태 조회 → AI decide →
 * actions 적용(DB·Redis)까지 전체 흐름을 실서비스에서 직접 돌려볼 수 있게 한다.
 *
 * <p>자동 인제스트 파이프라인(ItemProcessor)에 끼우기 전에, 실제 DB 상태로 엔진을 검증하는 용도다.
 * {@code woojuin.category-engine.enabled=true}일 때만 등록된다.
 */
@RestController
@RequestMapping("/api/category-engine")
@RequiredArgsConstructor
@ConditionalOnProperty(name = "woojuin.category-engine.enabled", havingValue = "true")
public class CategoryEngineController {

    private final CategoryEngineOrchestrator orchestrator;
    private final ItemRepository itemRepository;

    /** 아이템 하나를 카테고리 엔진으로 처리하고 적용 결과를 반환한다. */
    @AuthenticatedUser
    @PostMapping("/process/{itemId}")
    public ResponseEntity<ApiResponse<ProcessResponse>> process(@PathVariable Long itemId) {
        Item item = itemRepository.findById(itemId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "아이템 없음: " + itemId));
        String summary = item.getSummary() != null ? item.getSummary() : item.getContent();
        var outcome = orchestrator.process(
                item.getWorkspaceId(), item.getId(),
                item.getType() != null ? item.getType().name() : "URL",
                item.getTitle(), summary);
        return ResponseEntity.ok(ApiResponse.success(ProcessResponse.from(outcome)));
    }

    /** 적용 결과 요약(테스트 확인용). */
    public record ProcessResponse(
            boolean applied,
            List<Long> formalCategoryIds,
            String anchorName,
            String anchorType,
            String matchType,
            Long matchTargetId,
            List<String> actions,
            Long createdCandidateId,
            Long promotedCategoryId,
            boolean signalStored) {

        static ProcessResponse from(CategoryEngineOrchestrator.ProcessOutcome outcome) {
            if (!outcome.applied() || outcome.decision() == null) {
                return new ProcessResponse(false, List.of(), null, null, "SKIPPED", null,
                        List.of(), null, null, false);
            }
            CategoryEngineClient.DecideResult d = outcome.decision();
            var apply = outcome.apply();
            return new ProcessResponse(
                    true,
                    d.formalCategoryIds(),
                    d.categoryAnchor() != null ? d.categoryAnchor().name() : null,
                    d.categoryAnchor() != null ? d.categoryAnchor().type() : null,
                    d.match() != null ? d.match().type() : null,
                    d.match() != null ? d.match().targetId() : null,
                    d.actions().stream().map(CategoryEngineClient.EngineAction::type).toList(),
                    apply != null ? apply.createdCandidateId() : null,
                    apply != null ? apply.promotedCategoryId() : null,
                    apply != null && apply.signalStored());
        }
    }
}
