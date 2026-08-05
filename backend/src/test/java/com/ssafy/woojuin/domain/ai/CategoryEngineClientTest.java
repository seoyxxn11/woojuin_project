package com.ssafy.woojuin.domain.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.jsonPath;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

/**
 * category-engine decide 클라이언트 단위 테스트. MockRestServiceServer로 ai-test 서버 응답을
 * 흉내 내어, 요청 직렬화(camelCase 계약)와 응답 파싱(actions 포함)을 검증한다.
 */
class CategoryEngineClientTest {

    private CategoryEngineClient bind(MockRestServiceServer[] holder) {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://localhost");
        holder[0] = MockRestServiceServer.bindTo(builder).build();
        return new CategoryEngineClient(builder.build(), new ObjectMapper());
    }

    @Test
    void decide_promotedFormalReuse_parsesActionsAndMatch() {
        MockRestServiceServer[] holder = new MockRestServiceServer[1];
        CategoryEngineClient client = bind(holder);
        MockRestServiceServer server = holder[0];

        String response = """
                {"status":200,"message":"success","data":{
                  "workspaceId":10,"itemId":123,"formalCategoryIds":[1,7],"ambiguous":false,
                  "categoryAnchor":{"name":"SSAFY","normalizedName":"ssafy","type":"ENTITY",
                    "aliases":["싸피"],"specificEntities":[],"confidence":0.96},
                  "match":{"type":"PROMOTED_FORMAL","targetId":7,"method":"ENTITY_ALIAS"},
                  "actions":[
                    {"type":"LINK_FORMAL_CATEGORY","categoryId":1},
                    {"type":"LINK_FORMAL_CATEGORY","categoryId":7,"reason":"승격 카테고리 재사용"}
                  ]}}
                """;

        server.expect(requestTo("http://localhost/api/category-engine/decide"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(jsonPath("$.workspaceId").value(10))
                .andExpect(jsonPath("$.item.itemId").value(123))
                .andExpect(jsonPath("$.formalCategories[0].categoryId").value(1))
                .andRespond(withSuccess(response, MediaType.APPLICATION_JSON));

        CategoryEngineClient.DecideResult result = client.decide(
                10L,
                new CategoryEngineClient.Item(123L, "URL", "SSAFY 15기 합격 후기", "합격 준비 경험"),
                List.of(
                        new CategoryEngineClient.FormalCategory(1L, "학습·커리어", "SEED", null, null, List.of()),
                        new CategoryEngineClient.FormalCategory(
                                7L, "SSAFY", "AI_PROMOTED", "ENTITY", "ssafy", List.of("싸피"))),
                List.of(),
                null);

        server.verify();
        assertThat(result.formalCategoryIds()).containsExactly(1L, 7L);
        assertThat(result.match().type()).isEqualTo("PROMOTED_FORMAL");
        assertThat(result.match().targetId()).isEqualTo(7L);
        assertThat(result.categoryAnchor().normalizedName()).isEqualTo("ssafy");
        assertThat(result.actions()).hasSize(2);
        assertThat(result.actions().get(0).type()).isEqualTo("LINK_FORMAL_CATEGORY");
        assertThat(result.actions().get(1).categoryId()).isEqualTo(7L);
    }

    @Test
    void decide_storeSignal_parsesActionFields() {
        MockRestServiceServer[] holder = new MockRestServiceServer[1];
        CategoryEngineClient client = bind(holder);
        MockRestServiceServer server = holder[0];

        String response = """
                {"status":200,"message":"success","data":{
                  "workspaceId":10,"itemId":55,"formalCategoryIds":[3],"ambiguous":false,
                  "categoryAnchor":{"name":"새로운대상","normalizedName":"새로운대상","type":"ENTITY",
                    "aliases":[],"specificEntities":[],"confidence":0.9},
                  "match":{"type":"NONE"},
                  "actions":[
                    {"type":"LINK_FORMAL_CATEGORY","categoryId":3},
                    {"type":"STORE_SIGNAL","suggestedName":"새로운대상","anchorType":"ENTITY",
                     "normalizedAnchorName":"새로운대상","linkItemIds":[55]}
                  ]}}
                """;

        server.expect(requestTo("http://localhost/api/category-engine/decide"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(response, MediaType.APPLICATION_JSON));

        CategoryEngineClient.DecideResult result = client.decide(
                10L,
                new CategoryEngineClient.Item(55L, "URL", "제목", "요약"),
                List.of(new CategoryEngineClient.FormalCategory(3L, "장소·먹거리", "SEED", null, null, List.of())),
                List.of(),
                null);

        server.verify();
        assertThat(result.match().type()).isEqualTo("NONE");
        CategoryEngineClient.EngineAction store = result.actions().stream()
                .filter(a -> a.type().equals("STORE_SIGNAL")).findFirst().orElseThrow();
        assertThat(store.normalizedAnchorName()).isEqualTo("새로운대상");
        assertThat(store.linkItemIds()).containsExactly(55L);
    }
}
