package com.ssafy.woojuin.domain.item.processing.url;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import org.jsoup.nodes.Document;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * JDK HttpServer로 크롤러 사이드카를 흉내 내, HTTP 호출 → JSON 파싱 → Jsoup Document
 * 변환까지를 실제 네트워크(로컬 루프백)로 검증한다. PrivateNetworkGuard는 루프백을
 * 차단하므로 테스트 전용으로 통과시키는 가드를 주입한다.
 */
class ScraplingHtmlFetcherTest {

    private HttpServer server;
    private String baseUrl;
    private final ObjectMapper objectMapper = new ObjectMapper();

    /** 루프백(127.0.0.1)은 실 가드가 막으므로, 테스트에선 통과만 시키는 가드로 대체한다. */
    private final PrivateNetworkGuard allowAll = new PrivateNetworkGuard() {
        @Override
        public void verifyAllowed(java.net.URI uri) {
            // no-op
        }
    };

    @BeforeEach
    void startServer() throws Exception {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        baseUrl = "http://127.0.0.1:" + server.getAddress().getPort();
        server.start();
    }

    @AfterEach
    void stopServer() {
        server.stop(0);
    }

    private void respond(int status, String body) {
        server.createContext("/render", exchange -> {
            byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(status, bytes.length);
            exchange.getResponseBody().write(bytes);
            exchange.close();
        });
    }

    private ScraplingHtmlFetcher fetcher() {
        return new ScraplingHtmlFetcher(allowAll, objectMapper, baseUrl, 5000);
    }

    @Test
    void 크롤러가_준_html을_document로_감싼다() {
        respond(200, "{\"url\":\"https://final.example.com/x\",\"status\":200,"
                + "\"html\":\"<html><head><meta property=\\\"og:title\\\" content=\\\"OG\\\">"
                + "</head><body>본문</body></html>\"}");

        Document doc = fetcher().fetch("https://example.com/x");

        assertThat(doc.selectFirst("meta[property=og:title]").attr("content")).isEqualTo("OG");
        // 최종 URL이 baseUri로 반영되어야 상대경로 절대화가 맞는다.
        assertThat(doc.baseUri()).isEqualTo("https://final.example.com/x");
    }

    @Test
    void 비정상_상태코드면_예외를_던진다() {
        respond(502, "{\"detail\":\"render failed\"}");

        assertThatThrownBy(() -> fetcher().fetch("https://example.com/x"))
                .isInstanceOf(HtmlFetchException.class)
                .hasMessageContaining("502");
    }

    @Test
    void html이_비면_예외를_던진다() {
        respond(200, "{\"url\":\"https://example.com/x\",\"status\":200,\"html\":\"\"}");

        assertThatThrownBy(() -> fetcher().fetch("https://example.com/x"))
                .isInstanceOf(HtmlFetchException.class)
                .hasMessageContaining("빈 HTML");
    }
}
