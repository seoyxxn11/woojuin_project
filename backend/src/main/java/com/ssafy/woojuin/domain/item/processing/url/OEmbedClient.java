package com.ssafy.woojuin.domain.item.processing.url;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.Optional;
import java.util.regex.Pattern;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 알려진 제공자(YouTube, Vimeo 등)에 대해 oEmbed로 미리보기를 얻는다. oEmbed는 제공자가
 * 공식으로 주는 메타데이터라 OG 스크래핑보다 정확하고 안정적이므로 트랙 A에서 먼저 시도한다.
 *
 * <p>제공자 URL은 우리가 고정한 신뢰 엔드포인트이고, 사용자 URL은 쿼리 파라미터로만
 * 전달되므로(우리가 그 주소를 직접 받아오지 않음) SSRF 대상이 아니다.
 */
@Slf4j
@Component
public class OEmbedClient {

    /** URL 패턴 → oEmbed 엔드포인트(뒤에 인코딩된 url이 붙는다). */
    private record Provider(Pattern pattern, String endpoint) {
    }

    private static final List<Provider> PROVIDERS = List.of(
            new Provider(Pattern.compile("^https?://(www\\.)?youtube\\.com/watch\\?.*", Pattern.CASE_INSENSITIVE),
                    "https://www.youtube.com/oembed?format=json&url="),
            new Provider(Pattern.compile("^https?://(www\\.)?youtube\\.com/shorts/.*", Pattern.CASE_INSENSITIVE),
                    "https://www.youtube.com/oembed?format=json&url="),
            new Provider(Pattern.compile("^https?://vimeo\\.com/\\d+.*", Pattern.CASE_INSENSITIVE),
                    "https://vimeo.com/api/oembed.json?url="),
            new Provider(Pattern.compile("^https?://open\\.spotify\\.com/.*", Pattern.CASE_INSENSITIVE),
                    "https://open.spotify.com/oembed?url="),
            new Provider(Pattern.compile("^https?://soundcloud\\.com/.*", Pattern.CASE_INSENSITIVE),
                    "https://soundcloud.com/oembed?format=json&url="));

    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;

    public OEmbedClient(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(3))
                .followRedirects(HttpClient.Redirect.NORMAL)
                .build();
    }

    /** 알려진 제공자가 아니거나 호출이 실패하면 비어 있음을 반환 → 호출부가 OG 스크래핑으로 폴백. */
    public Optional<UrlPreview> fetch(String url) {
        Provider provider = PROVIDERS.stream()
                .filter(p -> p.pattern().matcher(url).matches())
                .findFirst()
                .orElse(null);
        if (provider == null) {
            return Optional.empty();
        }

        String endpoint = provider.endpoint() + URLEncoder.encode(url, StandardCharsets.UTF_8);
        try {
            HttpRequest request = HttpRequest.newBuilder(URI.create(endpoint))
                    .timeout(Duration.ofSeconds(4))
                    .header("User-Agent", "WoojuinBot/1.0")
                    .GET()
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) {
                log.debug("oEmbed 비정상 응답: status={}, url={}", response.statusCode(), url);
                return Optional.empty();
            }
            JsonNode json = objectMapper.readTree(response.body());
            return Optional.of(new UrlPreview(
                    text(json, "title"),
                    text(json, "thumbnail_url"),
                    text(json, "author_name")));
        } catch (Exception e) {
            log.debug("oEmbed 호출 실패, OG로 폴백: url={}, cause={}", url, e.toString());
            return Optional.empty();
        }
    }

    private String text(JsonNode node, String field) {
        JsonNode value = node.get(field);
        return (value != null && !value.isNull()) ? value.asText() : null;
    }
}
