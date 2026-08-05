package com.ssafy.woojuin.domain.ai;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;

/**
 * 증분 카테고리(앵커) 엔진 stateless 상태 전이 API({@code POST /api/category-engine/decide})
 * HTTP 클라이언트. ai-test 사이드카(ai/ai-test)를 호출한다.
 *
 * <p><b>상태를 저장하지 않는다.</b> 백엔드가 현재 워크스페이스 상태(정식 카테고리·후보
 * shortlist·잠정 신호)와 신규 아이템을 전달하면, AI 서버는 판단만 하고 백엔드가 DB·Redis에
 * 적용할 {@link EngineAction} 목록을 반환한다. 실제 연결·저장·트랜잭션은 백엔드가 처리한다.
 *
 * <p>실패 정책: 예외를 그대로 던진다(폴백은 호출부 책임). ai-mix 계약과 동일하게 공통 응답
 * 봉투 {@code {status, message, data}}의 data를 파싱한다.
 */
public class CategoryEngineClient {

    private final RestClient restClient;
    private final ObjectMapper objectMapper;

    public CategoryEngineClient(String baseUrl, Duration timeout, ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
        this.restClient = RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(new RestTemplateBuilder()
                        .setConnectTimeout(timeout)
                        .setReadTimeout(timeout)
                        .buildRequestFactory())
                .build();
    }

    /** 테스트용: 미리 구성한 RestClient 주입. */
    CategoryEngineClient(RestClient restClient, ObjectMapper objectMapper) {
        this.restClient = restClient;
        this.objectMapper = objectMapper;
    }

    // ---- 입력 모델 ----

    /** 신규 아이템(제목·요약만 전달, 본문 미사용). */
    public record Item(long itemId, String type, String title, String summary) {
    }

    /** 정식 카테고리(기본 시드 + 이미 승격된 대상 카테고리). */
    public record FormalCategory(
            long categoryId, String name, String origin,
            String anchorType, String normalizedAnchorName, List<String> aliases) {
    }

    /** 제목·요약 표본(후보 대표 데이터, 신호의 첫 데이터 등). */
    public record Sample(String title, String summary) {
    }

    /** 후보 shortlist 항목(백엔드가 앵커 정확 일치 또는 임베딩 Top-K로 좁혀 전달). */
    public record Candidate(
            long candidateId, String suggestedName,
            String anchorType, String normalizedAnchorName, List<String> aliases,
            int supportCount, Double similarity, List<Sample> representativeItems) {
    }

    /** 관련 잠정 신호(Redis에 보관된 첫 번째 신호). */
    public record Signal(
            Long signalId, Long firstItemId,
            String anchorType, String normalizedAnchorName, List<String> aliases,
            Sample firstItem, Double similarity) {
    }

    // ---- 출력 모델 ----

    public record CategoryAnchor(
            String name, String normalizedName, String type,
            List<String> aliases, List<String> specificEntities, double confidence) {
    }

    public record Match(String type, Long targetId, String method) {
    }

    /** 백엔드가 DB·Redis에 적용할 상태 변경 명령. type별로 필요한 필드만 채워진다. */
    public record EngineAction(
            String type, Long categoryId, Long candidateId, Integer supportCountAfter,
            String suggestedName, String anchorType, String normalizedAnchorName,
            List<String> aliases, List<Long> linkItemIds, String categoryName, String reason) {
    }

    public record DecideResult(
            long workspaceId, long itemId, List<Long> formalCategoryIds, boolean ambiguous,
            CategoryAnchor categoryAnchor, Match match, List<EngineAction> actions) {
    }

    // ---- 호출 ----

    /**
     * 상태 전이 판단 요청. 반환된 actions를 백엔드가 트랜잭션으로 DB·Redis에 반영한다.
     */
    public DecideResult decide(
            long workspaceId, Item item, List<FormalCategory> formalCategories,
            List<Candidate> candidateShortlist, Signal provisionalSignal) {

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("workspaceId", workspaceId);
        payload.put("item", itemPayload(item));
        payload.put("formalCategories", formalCategories.stream().map(this::formalPayload).toList());
        payload.put("candidateShortlist",
                candidateShortlist.stream().map(this::candidatePayload).toList());
        if (provisionalSignal != null) {
            payload.put("provisionalSignal", signalPayload(provisionalSignal));
        }

        JsonNode data = post("/api/category-engine/decide", payload);
        return parseResult(data);
    }

    // ---- 요청 직렬화 ----

    private Map<String, Object> itemPayload(Item item) {
        return payloadOf(
                "itemId", item.itemId(),
                "type", firstNonBlank(item.type(), "URL"),
                "title", truncate(item.title(), 1_000),
                "summary", truncate(item.summary(), 2_000));
    }

    private Map<String, Object> formalPayload(FormalCategory c) {
        return payloadOf(
                "categoryId", c.categoryId(),
                "name", truncate(c.name(), 100),
                "origin", firstNonBlank(c.origin(), "SEED"),
                "anchorType", c.anchorType(),
                "normalizedAnchorName", truncate(c.normalizedAnchorName(), 100),
                "aliases", c.aliases() == null ? List.of() : c.aliases());
    }

    private Map<String, Object> candidatePayload(Candidate c) {
        return payloadOf(
                "candidateId", c.candidateId(),
                "suggestedName", truncate(c.suggestedName(), 100),
                "anchorType", c.anchorType(),
                "normalizedAnchorName", truncate(c.normalizedAnchorName(), 100),
                "aliases", c.aliases() == null ? List.of() : c.aliases(),
                "supportCount", c.supportCount(),
                "similarity", c.similarity(),
                "representativeItems", samplesPayload(c.representativeItems()));
    }

    private Map<String, Object> signalPayload(Signal s) {
        return payloadOf(
                "signalId", s.signalId(),
                "firstItemId", s.firstItemId(),
                "anchorType", s.anchorType(),
                "normalizedAnchorName", truncate(s.normalizedAnchorName(), 100),
                "aliases", s.aliases() == null ? List.of() : s.aliases(),
                "firstItem", s.firstItem() == null ? Map.of() : samplePayload(s.firstItem()),
                "similarity", s.similarity());
    }

    private List<Map<String, Object>> samplesPayload(List<Sample> samples) {
        if (samples == null) {
            return List.of();
        }
        return samples.stream().map(this::samplePayload).toList();
    }

    private Map<String, Object> samplePayload(Sample s) {
        return payloadOf(
                "title", truncate(s.title(), 300),
                "summary", truncate(s.summary(), 2_000));
    }

    // ---- 응답 파싱 ----

    private DecideResult parseResult(JsonNode data) {
        List<Long> formalIds = new ArrayList<>();
        data.path("formalCategoryIds").forEach(node -> formalIds.add(node.asLong()));

        JsonNode anchorNode = data.path("categoryAnchor");
        CategoryAnchor anchor = new CategoryAnchor(
                textOrNull(anchorNode.path("name")),
                textOrNull(anchorNode.path("normalizedName")),
                textOrNull(anchorNode.path("type")),
                stringList(anchorNode.path("aliases")),
                stringList(anchorNode.path("specificEntities")),
                anchorNode.path("confidence").asDouble(0.0));

        JsonNode matchNode = data.path("match");
        Match match = new Match(
                textOrNull(matchNode.path("type")),
                matchNode.path("targetId").isMissingNode() || matchNode.path("targetId").isNull()
                        ? null : matchNode.path("targetId").asLong(),
                textOrNull(matchNode.path("method")));

        List<EngineAction> actions = new ArrayList<>();
        data.path("actions").forEach(node -> actions.add(parseAction(node)));

        return new DecideResult(
                data.path("workspaceId").asLong(),
                data.path("itemId").asLong(),
                formalIds,
                data.path("ambiguous").asBoolean(false),
                anchor, match, actions);
    }

    private EngineAction parseAction(JsonNode node) {
        return new EngineAction(
                textOrNull(node.path("type")),
                longOrNull(node.path("categoryId")),
                longOrNull(node.path("candidateId")),
                node.path("supportCountAfter").isMissingNode() || node.path("supportCountAfter").isNull()
                        ? null : node.path("supportCountAfter").asInt(),
                textOrNull(node.path("suggestedName")),
                textOrNull(node.path("anchorType")),
                textOrNull(node.path("normalizedAnchorName")),
                stringList(node.path("aliases")),
                longList(node.path("linkItemIds")),
                textOrNull(node.path("categoryName")),
                textOrNull(node.path("reason")));
    }

    // ---- 공통 헬퍼(AiMixClient와 동일 패턴) ----

    private JsonNode post(String path, Map<String, Object> body) {
        String raw = restClient.post()
                .uri(path)
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.APPLICATION_JSON)
                .body(body)
                .retrieve()
                .body(String.class);
        if (raw == null || raw.isBlank()) {
            throw new IllegalStateException("category-engine 응답이 비어 있음: " + path);
        }
        try {
            return objectMapper.readTree(raw).path("data");
        } catch (Exception e) {
            throw new IllegalStateException("category-engine 응답 파싱 실패: " + path, e);
        }
    }

    private static Map<String, Object> payloadOf(Object... pairs) {
        Map<String, Object> payload = new LinkedHashMap<>();
        for (int i = 0; i < pairs.length; i += 2) {
            if (pairs[i + 1] != null) {
                payload.put((String) pairs[i], pairs[i + 1]);
            }
        }
        return payload;
    }

    private static List<String> stringList(JsonNode node) {
        List<String> list = new ArrayList<>();
        if (node.isArray()) {
            node.forEach(child -> {
                String text = textOrNull(child);
                if (text != null) {
                    list.add(text);
                }
            });
        }
        return list;
    }

    private static List<Long> longList(JsonNode node) {
        if (!node.isArray() || node.isEmpty()) {
            return null;
        }
        List<Long> list = new ArrayList<>();
        node.forEach(child -> list.add(child.asLong()));
        return list;
    }

    private static Long longOrNull(JsonNode node) {
        return (node.isMissingNode() || node.isNull()) ? null : node.asLong();
    }

    private static String truncate(String value, int maxLength) {
        if (value == null || value.isBlank()) {
            return null;
        }
        String stripped = value.strip();
        return stripped.length() <= maxLength ? stripped : stripped.substring(0, maxLength);
    }

    private static String firstNonBlank(String first, String second) {
        return (first != null && !first.isBlank()) ? first : ((second != null && !second.isBlank()) ? second : null);
    }

    private static String textOrNull(JsonNode node) {
        if (node.isMissingNode() || node.isNull()) {
            return null;
        }
        String text = node.asText("");
        return text.isBlank() ? null : text;
    }
}
