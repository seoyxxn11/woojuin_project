package com.ssafy.woojuin.domain.item.processing.url;

import java.io.IOException;
import java.net.URI;
import java.net.URISyntaxException;
import org.jsoup.Connection;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Jsoup 기반 {@link HtmlFetcher}. SSRF 가드를 통과한 주소만, 리다이렉트를 직접 따라가며
 * 받아온다. Jsoup의 자동 리다이렉트를 끄고 홉마다 {@link PrivateNetworkGuard}로 다시
 * 검사하는 이유는, 외부 URL이 302로 내부 주소를 가리키는 우회를 막기 위함이다.
 */
@Component
public class JsoupHtmlFetcher implements HtmlFetcher {

    /** 실제 브라우저처럼 보이지 않으면 OG 태그를 안 주는 사이트가 있어 UA를 지정한다. */
    private static final String USER_AGENT =
            "Mozilla/5.0 (compatible; WoojuinBot/1.0; +https://woojuin.app/bot)";

    private final PrivateNetworkGuard guard;
    private final int timeoutMs;
    private final int maxBodyBytes;
    private final int maxRedirects;

    public JsoupHtmlFetcher(
            PrivateNetworkGuard guard,
            @Value("${woojuin.fetch.timeout-ms:5000}") int timeoutMs,
            @Value("${woojuin.fetch.max-body-bytes:3145728}") int maxBodyBytes,
            @Value("${woojuin.fetch.max-redirects:5}") int maxRedirects) {
        this.guard = guard;
        this.timeoutMs = timeoutMs;
        this.maxBodyBytes = maxBodyBytes;
        this.maxRedirects = maxRedirects;
    }

    @Override
    public Document fetch(String url) {
        String current = url;
        for (int hop = 0; hop <= maxRedirects; hop++) {
            URI uri = parse(current);
            guard.verifyAllowed(uri);

            Connection.Response response;
            try {
                response = Jsoup.connect(current)
                        .userAgent(USER_AGENT)
                        .timeout(timeoutMs)
                        .maxBodySize(maxBodyBytes)
                        .followRedirects(false)   // 홉마다 직접 검사하려고 끈다
                        .ignoreHttpErrors(true)   // 4xx/5xx도 예외 대신 응답으로 받아 상태코드로 판단
                        .ignoreContentType(true)  // content-type 검증은 아래에서 직접
                        .execute();
            } catch (IOException e) {
                throw new HtmlFetchException("HTML 요청 실패: " + current, e);
            }

            int status = response.statusCode();
            if (isRedirect(status)) {
                String location = response.header("Location");
                if (location == null || location.isBlank()) {
                    throw new HtmlFetchException("리다이렉트에 Location 헤더가 없음: " + current);
                }
                current = uri.resolve(location).toString();   // 상대 Location 절대화
                continue;
            }
            if (status >= 400) {
                throw new HtmlFetchException("HTML 응답 오류: status=" + status + ", url=" + current);
            }

            String contentType = response.contentType();
            if (contentType != null && !contentType.contains("html")) {
                throw new HtmlFetchException("HTML이 아닌 응답: contentType=" + contentType + ", url=" + current);
            }
            try {
                return response.parse();
            } catch (IOException e) {
                throw new HtmlFetchException("HTML 파싱 실패: " + current, e);
            }
        }
        throw new HtmlFetchException("리다이렉트 한도(" + maxRedirects + ") 초과: " + url);
    }

    private URI parse(String url) {
        try {
            return new URI(url);
        } catch (URISyntaxException e) {
            throw new HtmlFetchException("잘못된 URL: " + url, e);
        }
    }

    private boolean isRedirect(int status) {
        return status == 301 || status == 302 || status == 303 || status == 307 || status == 308;
    }
}
