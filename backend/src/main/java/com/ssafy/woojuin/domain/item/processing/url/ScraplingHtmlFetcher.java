package com.ssafy.woojuin.domain.item.processing.url;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import lombok.extern.slf4j.Slf4j;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Scrapling 크롤러 사이드카({@code crawler/})를 호출하는 {@link HtmlFetcher}.
 *
 * <p>Jsoup은 단순 HTTP GET이라 JS 렌더링 SPA나 봇 차단(Cloudflare 등) 페이지에서
 * 빈 껍데기만 받는다. 그럴 때 {@link FallbackHtmlFetcher}가 이 구현으로 폴백한다.
 * 크롤러가 StealthyFetcher(스텔스 브라우저)로 렌더한 최종 HTML을 받아
 * {@code Jsoup.parse}로 감싸므로, 하위 OG 스크래퍼·본문 추출은 그대로 동작한다.
 *
 * <p>{@link OEmbedClient}와 같은 방식으로 JDK {@code HttpClient} + Jackson을 쓴다.
 * 브라우저 렌더는 수 초가 걸릴 수 있어 요청 타임아웃을 크롤러 자체 타임아웃보다
 * 넉넉히 잡는다.
 */
@Slf4j
@Component
public class ScraplingHtmlFetcher implements HtmlFetcher {

    private final PrivateNetworkGuard guard;
    private final ObjectMapper objectMapper;
    private final String renderEndpoint;
    private final Duration requestTimeout;
    private final HttpClient httpClient;

    public ScraplingHtmlFetcher(
            PrivateNetworkGuard guard,
            ObjectMapper objectMapper,
            @Value("${woojuin.crawler.base-url:http://localhost:8001}") String baseUrl,
            @Value("${woojuin.crawler.timeout-ms:40000}") int timeoutMs) {
        this.guard = guard;
        this.objectMapper = objectMapper;
        this.renderEndpoint = baseUrl.replaceAll("/+$", "") + "/render";
        this.requestTimeout = Duration.ofMillis(timeoutMs);
        // HTTP/1.1 고정. 기본값 HTTP/2는 cleartext(http)에서 h2c 업그레이드를 시도하는데
        // uvicorn이 이를 거부하며("Unsupported upgrade request") 요청 본문이 유실돼
        // FastAPI가 422(body missing)를 낸다. 크롤러는 HTTP/1.1만 쓰므로 명시한다.
        this.httpClient = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(Duration.ofSeconds(3))
                .build();
    }

    /**
     * SSRF 가드는 우리가 요청을 넘기기 전 초기 URL에 대해 확인한다. 다만 크롤러는
     * 브라우저 안에서 리다이렉트를 직접 따라가므로 홉 단위 재검사는 크롤러 몫이다
     * (사이드카는 우리가 통제하는 신뢰 서비스라는 전제).
     */
    @Override
    public Document fetch(String url) {
        guard.verifyAllowed(parse(url));

        String requestBody = renderRequestJson(url);
        HttpResponse<String> response;
        try {
            HttpRequest request = HttpRequest.newBuilder(URI.create(renderEndpoint))
                    .timeout(requestTimeout)
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(requestBody, StandardCharsets.UTF_8))
                    .build();
            response = httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        } catch (Exception e) {
            throw new HtmlFetchException("크롤러 호출 실패: " + url, e);
        }

        if (response.statusCode() != 200) {
            throw new HtmlFetchException(
                    "크롤러 비정상 응답: status=" + response.statusCode() + ", url=" + url);
        }

        JsonNode json;
        try {
            json = objectMapper.readTree(response.body());
        } catch (Exception e) {
            throw new HtmlFetchException("크롤러 응답 파싱 실패: " + url, e);
        }

        String html = text(json, "html");
        if (html == null || html.isBlank()) {
            throw new HtmlFetchException("크롤러가 빈 HTML을 반환: " + url);
        }
        // 최종 URL(리다이렉트 반영)을 baseUri로 줘야 상대경로 og:image 절대화가 맞는다.
        String finalUrl = firstNonBlank(text(json, "url"), url);
        return Jsoup.parse(html, finalUrl);
    }

    private String renderRequestJson(String url) {
        try {
            return objectMapper.writeValueAsString(java.util.Map.of("url", url));
        } catch (Exception e) {
            throw new HtmlFetchException("크롤러 요청 직렬화 실패: " + url, e);
        }
    }

    private URI parse(String url) {
        try {
            return new URI(url);
        } catch (Exception e) {
            throw new HtmlFetchException("잘못된 URL: " + url, e);
        }
    }

    private String text(JsonNode node, String field) {
        JsonNode value = node.get(field);
        return (value != null && !value.isNull()) ? value.asText() : null;
    }

    private String firstNonBlank(String a, String b) {
        return (a != null && !a.isBlank()) ? a : b;
    }
}
