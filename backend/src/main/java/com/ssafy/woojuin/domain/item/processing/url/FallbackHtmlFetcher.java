package com.ssafy.woojuin.domain.item.processing.url;

import lombok.extern.slf4j.Slf4j;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Component;

/**
 * 두 페처를 엮는 기본 {@link HtmlFetcher}. 빠른 경로로 Jsoup을 먼저 쓰고, 그 결과가
 * 쓸모없을 때만 무거운 Scrapling 크롤러로 폴백한다. {@code @Primary}라 이 도메인의
 * 모든 소비자({@code UrlItemProcessor}·{@code UrlBatchExportRunner})가 별도 수정
 * 없이 이 체인을 주입받는다.
 *
 * <p><b>폴백 트리거</b> (둘 중 하나):
 * <ul>
 *   <li>Jsoup이 예외로 실패 — 403/503 봇 차단, 타임아웃 등</li>
 *   <li>Jsoup은 200을 받았지만 결과가 빈약함 — JS 렌더링 SPA의 빈 껍데기 등.
 *       og:title도 없고 본문 텍스트도 임계치 미만이면 브라우저 렌더가 필요하다고 본다.</li>
 * </ul>
 *
 * <p><b>실패 처리</b>: 크롤러 폴백까지 실패해도, Jsoup이 그나마 문서를 받아뒀다면
 * 그걸(빈약하더라도) 돌려준다 — best-effort. Jsoup·크롤러가 모두 실패했을 때만
 * 원래 Jsoup 예외를 던진다. 크롤러가 꺼져 있으면({@code woojuin.crawler.enabled=false})
 * 폴백을 아예 시도하지 않고 Jsoup 동작을 그대로 노출한다.
 */
@Slf4j
@Primary
@Component
public class FallbackHtmlFetcher implements HtmlFetcher {

    private final HtmlFetcher jsoup;
    private final HtmlFetcher crawler;
    private final boolean crawlerEnabled;
    private final int minTextLength;

    public FallbackHtmlFetcher(
            @Qualifier("jsoupHtmlFetcher") HtmlFetcher jsoup,
            @Qualifier("scraplingHtmlFetcher") HtmlFetcher crawler,
            @Value("${woojuin.crawler.enabled:false}") boolean crawlerEnabled,
            @Value("${woojuin.crawler.fallback-min-text-length:200}") int minTextLength) {
        this.jsoup = jsoup;
        this.crawler = crawler;
        this.crawlerEnabled = crawlerEnabled;
        this.minTextLength = minTextLength;
    }

    @Override
    public Document fetch(String url) {
        Document jsoupDoc = null;
        HtmlFetchException jsoupError = null;
        try {
            jsoupDoc = jsoup.fetch(url);
            if (!crawlerEnabled || looksSufficient(jsoupDoc)) {
                return jsoupDoc;
            }
            log.info("Jsoup 결과가 빈약함, 스텔스 크롤러로 폴백: url={}", url);
        } catch (HtmlFetchException e) {
            if (!crawlerEnabled) {
                throw e;
            }
            jsoupError = e;
            log.info("Jsoup fetch 실패, 스텔스 크롤러로 폴백: url={}, cause={}", url, e.getMessage());
        }

        try {
            return crawler.fetch(url);
        } catch (HtmlFetchException e) {
            if (jsoupDoc != null) {
                // 크롤러가 못 뚫어도 Jsoup이 받아둔 빈약한 문서라도 쓴다.
                log.info("크롤러 폴백도 실패, Jsoup 결과 사용: url={}, cause={}", url, e.getMessage());
                return jsoupDoc;
            }
            log.info("크롤러 폴백 실패(Jsoup도 실패): url={}, cause={}", url, e.getMessage());
            throw (jsoupError != null) ? jsoupError : e;
        }
    }

    /**
     * Jsoup이 받은 문서가 이미 쓸 만한지 가볍게 판단한다. og:title이 있으면 최소한의
     * 미리보기가 나오므로 충분하다고 보고, 없더라도 본문 텍스트가 임계치 이상이면
     * 정적 HTML만으로 내용이 담긴 것이다. 둘 다 아니면(SPA 껍데기·차단 페이지) 폴백.
     */
    private boolean looksSufficient(Document doc) {
        if (doc.selectFirst("meta[property=og:title]") != null) {
            return true;
        }
        Element body = doc.body();
        String text = (body != null) ? body.text().trim() : "";
        return text.length() >= minTextLength;
    }
}
