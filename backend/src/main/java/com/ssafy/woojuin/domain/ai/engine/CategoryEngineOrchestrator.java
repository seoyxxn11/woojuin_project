package com.ssafy.woojuin.domain.ai.engine;

import com.ssafy.woojuin.domain.ai.CategoryEngineClient;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

/**
 * 카테고리 엔진 파이프라인 오케스트레이터. 한 아이템에 대해 현재 상태를 모아 AI decide를 부르고,
 * 반환된 actions를 백엔드 상태에 반영한다.
 *
 * <p><b>트랜잭션 경계</b>: {@link #plan}은 AI(LLM) 호출과 짧은 읽기만 한다 — 트랜잭션 밖에서
 * 부른다(느린 외부 호출로 커넥션을 점유하지 않게). {@link CategoryEngineActionExecutor#apply}만
 * 자체 짧은 트랜잭션으로 DB에 반영한다.
 *
 * <p>{@code woojuin.category-engine.enabled=true}일 때만 등록된다(CategoryEngineClient도 동일 조건).
 */
@Slf4j
@Service
@RequiredArgsConstructor
@ConditionalOnProperty(name = "woojuin.category-engine.enabled", havingValue = "true")
public class CategoryEngineOrchestrator {

    private final CategoryEngineClient client;
    private final CategoryEngineStateGatherer gatherer;
    private final CategoryEngineSignalStore signalStore;
    private final CategoryEngineActionExecutor executor;

    /** 처리 결과. applied=false면 AI 실패로 엔진을 건너뜀(호출부는 기본 분류 유지). */
    public record ProcessOutcome(
            boolean applied,
            CategoryEngineClient.DecideResult decision,
            CategoryEngineActionExecutor.ApplyResult apply) {
    }

    /** 상태 조회 → decide → apply. AI 실패 시 applied=false(폴백은 호출부). */
    public ProcessOutcome process(long workspaceId, long itemId, String type, String title, String summary) {
        CategoryEngineClient.DecideResult decision = plan(workspaceId, itemId, type, title, summary);
        if (decision == null) {
            return new ProcessOutcome(false, null, null);
        }
        CategoryEngineActionExecutor.ApplyResult applied =
                executor.apply(workspaceId, itemId, title, summary, decision);
        return new ProcessOutcome(true, decision, applied);
    }

    /**
     * 상태 조회 + decide(트랜잭션 밖). 매칭이 없고 같은 앵커의 대기 신호가 있으면 2번째 데이터로
     * 보고 신호를 실어 한 번 더 판단한다(신호→후보 전환). AI 실패면 null.
     */
    public CategoryEngineClient.DecideResult plan(
            long workspaceId, long itemId, String type, String title, String summary) {
        CategoryEngineClient.Item item = new CategoryEngineClient.Item(
                itemId, normalizeType(type), title, summary);
        var formals = gatherer.formalCategories(workspaceId);
        var candidates = gatherer.candidateShortlist(workspaceId);

        CategoryEngineClient.DecideResult first;
        try {
            first = client.decide(workspaceId, item, formals, candidates, null);
        } catch (Exception e) {
            log.warn("category-engine decide 실패(무시): ws={} itemId={}", workspaceId, itemId, e);
            return null;
        }

        String matchType = first.match() != null ? first.match().type() : "NONE";
        if (!"NONE".equals(matchType)) {
            return first;   // 승격 카테고리/후보 매칭 → 그대로 적용
        }

        // 매칭 없음 → 같은 앵커의 대기 신호가 있으면 2번째 데이터로 보고 후보 전환 판단
        String norm = first.categoryAnchor() != null ? first.categoryAnchor().normalizedName() : null;
        if (norm == null || norm.isBlank()) {
            return first;
        }
        CategoryEngineSignalStore.StoredSignal sig = signalStore.find(workspaceId, norm);
        if (sig == null) {
            return first;   // 첫 데이터 → STORE_SIGNAL 적용
        }
        CategoryEngineClient.Signal signal = new CategoryEngineClient.Signal(
                sig.signalId(), sig.firstItemId(), sig.anchorType(), sig.normalizedAnchorName(),
                sig.aliases(),
                new CategoryEngineClient.Sample(sig.firstTitle(), sig.firstSummary()), null);
        try {
            return client.decide(workspaceId, item, formals, candidates, signal);
        } catch (Exception e) {
            log.warn("category-engine 2차 decide 실패(신호 전환) — STORE로 폴백: ws={} itemId={}",
                    workspaceId, itemId, e);
            return first;
        }
    }

    private static String normalizeType(String type) {
        if (type == null) {
            return "URL";
        }
        String upper = type.toUpperCase();
        return switch (upper) {
            case "URL", "MEMO", "IMAGE" -> upper;
            default -> "URL";
        };
    }
}
