package com.ssafy.woojuin.domain.ai.engine;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.ArgumentMatchers.notNull;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.ssafy.woojuin.domain.ai.CategoryEngineClient;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class CategoryEngineOrchestratorTest {

    @Mock CategoryEngineClient client;
    @Mock CategoryEngineStateGatherer gatherer;
    @Mock CategoryEngineSignalStore signalStore;
    @Mock CategoryEngineActionExecutor executor;

    @InjectMocks CategoryEngineOrchestrator orchestrator;

    private static CategoryEngineClient.DecideResult resultWith(String matchType, String anchorNorm,
            List<CategoryEngineClient.EngineAction> actions) {
        var anchor = new CategoryEngineClient.CategoryAnchor("A", anchorNorm, "ENTITY", List.of(), List.of(), 0.9);
        var match = new CategoryEngineClient.Match(matchType, matchType.equals("NONE") ? null : 7L, "ENTITY_EXACT");
        return new CategoryEngineClient.DecideResult(10L, 1L, List.of(2L), false, anchor, match, actions);
    }

    private static CategoryEngineClient.EngineAction action(String type) {
        return new CategoryEngineClient.EngineAction(type, null, null, null, null, null, null, null, null, null, null);
    }

    @Test
    void matchedCandidate_appliesFirstDecision_noSignalLookup() {
        var first = resultWith("CANDIDATE", "ssafy", List.of(action("LINK_CANDIDATE")));
        when(client.decide(anyLong(), any(), any(), any(), isNull())).thenReturn(first);

        var outcome = orchestrator.process(10L, 1L, "URL", "제목", "요약");

        assertThat(outcome.applied()).isTrue();
        verify(executor).apply(eq(10L), eq(1L), any(), any(), eq(first));
        verify(signalStore, never()).find(anyLong(), any());  // 매칭됐으면 신호 조회 안 함
    }

    @Test
    void noMatch_noSignal_appliesStoreSignal() {
        var first = resultWith("NONE", "newthing", List.of(action("STORE_SIGNAL")));
        when(client.decide(anyLong(), any(), any(), any(), isNull())).thenReturn(first);
        when(signalStore.find(10L, "newthing")).thenReturn(null);

        var outcome = orchestrator.process(10L, 1L, "URL", "t", "s");

        assertThat(outcome.applied()).isTrue();
        verify(executor).apply(eq(10L), eq(1L), any(), any(), eq(first));
    }

    @Test
    void noMatch_withWaitingSignal_secondDecideConvertsToCandidate() {
        var first = resultWith("NONE", "ssafy", List.of(action("STORE_SIGNAL")));
        var second = resultWith("SIGNAL", "ssafy", List.of(action("CREATE_CANDIDATE")));
        when(client.decide(anyLong(), any(), any(), any(), isNull())).thenReturn(first);
        when(client.decide(anyLong(), any(), any(), any(), notNull())).thenReturn(second);
        when(signalStore.find(10L, "ssafy")).thenReturn(new CategoryEngineSignalStore.StoredSignal(
                100L, 1L, "ENTITY", "SSAFY", List.of("싸피"), "SSAFY 합격", "후기"));

        var outcome = orchestrator.process(10L, 2L, "URL", "SSAFY 교육과정", "커리큘럼");

        assertThat(outcome.applied()).isTrue();
        verify(executor).apply(eq(10L), eq(2L), any(), any(), eq(second));  // 2차(신호 전환) 결과 적용
    }

    @Test
    void aiFailure_notApplied() {
        when(client.decide(anyLong(), any(), any(), any(), isNull()))
                .thenThrow(new RuntimeException("서버 오류"));

        var outcome = orchestrator.process(10L, 1L, "URL", "t", "s");

        assertThat(outcome.applied()).isFalse();
        verify(executor, never()).apply(anyLong(), anyLong(), any(), any(), any());
    }
}
