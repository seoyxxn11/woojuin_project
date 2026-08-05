package com.ssafy.woojuin.domain.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Duration;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

/**
 * 실행 중인 ai-test 서버(POST /api/category-engine/decide)에 대한 <b>실제 호출 스모크</b>.
 *
 * <p>DB·Redis를 쓰지 않고 fixture(테스트 객체)로 워크스페이스 상태를 구성해 5개 시나리오를
 * 검증한다. 실제 LLM 호출이 나가므로 기본 CI에서는 건너뛴다 — 환경변수
 * {@code CATEGORY_ENGINE_SMOKE=true}일 때만 실행한다. 서버 주소는
 * {@code CATEGORY_ENGINE_BASE_URL}(기본 http://127.0.0.1:8002).
 *
 * <pre>{@code
 *   # 1) ai-test 서버 기동:  cd ai/ai-test && .venv/Scripts/python -m uvicorn app:app --port 8002
 *   # 2) 스모크:  CATEGORY_ENGINE_SMOKE=true ./gradlew test --tests *CategoryEngineSmokeTest
 * }</pre>
 */
@EnabledIfEnvironmentVariable(named = "CATEGORY_ENGINE_SMOKE", matches = "true")
class CategoryEngineSmokeTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private static String baseUrl() {
        String url = System.getenv("CATEGORY_ENGINE_BASE_URL");
        return (url == null || url.isBlank()) ? "http://127.0.0.1:8002" : url;
    }

    private CategoryEngineClient client() {
        return new CategoryEngineClient(baseUrl(), Duration.ofSeconds(60), MAPPER);
    }

    private static List<CategoryEngineClient.FormalCategory> seeds() {
        return List.of(
                new CategoryEngineClient.FormalCategory(1L, "생활·건강", "SEED", null, null, List.of()),
                new CategoryEngineClient.FormalCategory(2L, "학습·커리어", "SEED", null, null, List.of()),
                new CategoryEngineClient.FormalCategory(3L, "장소·먹거리", "SEED", null, null, List.of()),
                new CategoryEngineClient.FormalCategory(4L, "소비·금융", "SEED", null, null, List.of()),
                new CategoryEngineClient.FormalCategory(5L, "문화·아이디어", "SEED", null, null, List.of()));
    }

    private static List<String> types(CategoryEngineClient.DecideResult r) {
        return r.actions().stream().map(CategoryEngineClient.EngineAction::type).toList();
    }

    private static void dump(String scenario, CategoryEngineClient.DecideResult r) {
        System.out.println("=== " + scenario + " ===");
        System.out.println("  formalCategoryIds=" + r.formalCategoryIds() + " ambiguous=" + r.ambiguous());
        System.out.println("  anchor=" + r.categoryAnchor().name() + " / norm=" + r.categoryAnchor().normalizedName()
                + " type=" + r.categoryAnchor().type() + " conf=" + r.categoryAnchor().confidence());
        System.out.println("  match=" + r.match().type() + " target=" + r.match().targetId()
                + " method=" + r.match().method());
        for (CategoryEngineClient.EngineAction a : r.actions()) {
            System.out.println("  action " + a.type()
                    + " categoryId=" + a.categoryId()
                    + " candidateId=" + a.candidateId()
                    + " supportAfter=" + a.supportCountAfter()
                    + " linkItemIds=" + a.linkItemIds()
                    + " norm=" + a.normalizedAnchorName()
                    + " reason=" + a.reason());
        }
    }

    @Test
    void scenario1_firstItem_storeSignal() {
        var item = new CategoryEngineClient.Item(1L, "URL", "SSAFY 15기 합격 후기",
                "SSAFY 지원 과정과 합격 준비 경험을 정리한 후기");
        var r = client().decide(10L, item, seeds(), List.of(), null);
        dump("1. 첫 동일 대상 → STORE_SIGNAL", r);
        assertThat(types(r)).contains("LINK_FORMAL_CATEGORY", "STORE_SIGNAL");
    }

    @Test
    void scenario2_secondItemWithSignal_createCandidate() {
        var signal = new CategoryEngineClient.Signal(
                100L, 1L, "ENTITY", "SSAFY", List.of("싸피"),
                new CategoryEngineClient.Sample("SSAFY 15기 합격 후기", "합격 준비 경험"), null);
        var item = new CategoryEngineClient.Item(2L, "URL", "SSAFY 교육과정 소개",
                "SSAFY의 12개월 커리큘럼과 프로젝트 과정을 소개한다");
        var r = client().decide(10L, item, seeds(), List.of(), signal);
        dump("2. 두 번째 + 신호 → CREATE_CANDIDATE", r);
        assertThat(types(r)).contains("CREATE_CANDIDATE");
        var create = r.actions().stream().filter(a -> a.type().equals("CREATE_CANDIDATE"))
                .findFirst().orElseThrow();
        assertThat(create.linkItemIds()).contains(1L, 2L);  // 두 itemId 연결
    }

    @Test
    void scenario3_thirdItemWithCandidate_linkAndPromote() {
        var candidate = new CategoryEngineClient.Candidate(
                7L, "SSAFY", "ENTITY", "SSAFY", List.of("싸피"), 2, 0.6,
                List.of(new CategoryEngineClient.Sample("SSAFY 합격 후기", "합격 경험"),
                        new CategoryEngineClient.Sample("SSAFY 교육과정 소개", "커리큘럼")));
        var item = new CategoryEngineClient.Item(3L, "URL", "SSAFY 취업 후기",
                "SSAFY 수료 후 취업에 성공한 과정을 정리한 후기");
        var r = client().decide(10L, item, seeds(), List.of(candidate), null);
        dump("3. 세 번째 + 후보 → LINK_CANDIDATE + 승격(ENTITY 규칙)", r);
        assertThat(types(r)).contains("LINK_CANDIDATE");
        var link = r.actions().stream().filter(a -> a.type().equals("LINK_CANDIDATE"))
                .findFirst().orElseThrow();
        assertThat(link.supportCountAfter()).isEqualTo(3);
        assertThat(types(r)).contains("PROMOTE_CANDIDATE");  // ENTITY 3건 → 규칙 기반 승격
    }

    @Test
    void scenario4_promotedFormalExists_linkBaseAndPromoted() {
        var formals = new java.util.ArrayList<>(seeds());
        formals.add(new CategoryEngineClient.FormalCategory(
                7L, "SSAFY", "AI_PROMOTED", "ENTITY", "SSAFY", List.of("싸피", "삼성 청년 SW 아카데미")));
        var item = new CategoryEngineClient.Item(4L, "URL", "SSAFY 16기 모집 안내",
                "SSAFY 16기 지원 자격과 모집 일정 안내");
        var r = client().decide(10L, item, formals, List.of(), null);
        dump("4. 승격 카테고리 존재 → 기본+승격 연결", r);
        assertThat(r.match().type()).isEqualTo("PROMOTED_FORMAL");
        assertThat(r.match().targetId()).isEqualTo(7L);
        assertThat(r.formalCategoryIds()).contains(7L);
        long links = r.actions().stream().filter(a -> a.type().equals("LINK_FORMAL_CATEGORY")).count();
        assertThat(links).isGreaterThanOrEqualTo(2);  // 기본 + 승격
    }

    @Test
    void scenario5_serverError_isDetectable() {
        // 죽은 포트 → 연결 실패. 클라이언트가 예외를 던져 백엔드가 감지 가능(→ 기본 분류만 유지).
        var deadClient = new CategoryEngineClient("http://127.0.0.1:59999", Duration.ofSeconds(3), MAPPER);
        var item = new CategoryEngineClient.Item(5L, "URL", "제목", "요약");
        assertThatThrownBy(() -> deadClient.decide(10L, item, seeds(), List.of(), null))
                .isInstanceOf(Exception.class);
        System.out.println("=== 5. 서버 오류 → 예외로 감지됨(백엔드는 기본 분류 유지) ===");
    }
}
