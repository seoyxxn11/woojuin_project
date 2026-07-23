package com.ssafy.woojuin.domain.item.processing.url;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.concurrent.atomic.AtomicInteger;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.junit.jupiter.api.Test;

/**
 * 폴백 오케스트레이션만 검증한다. HtmlFetcher가 함수형 인터페이스라 실제 네트워크
 * 없이 람다로 각 페처를 흉내 낸다.
 */
class FallbackHtmlFetcherTest {

    private static final String URL = "https://example.com/a";

    private Document richDoc() {
        return Jsoup.parse("<html><head><meta property=\"og:title\" content=\"T\">"
                + "</head><body><p>충분한 본문</p></body></html>", URL);
    }

    private Document emptyShell() {
        // og:title 없음 + 본문 텍스트 거의 없음 → SPA 껍데기로 간주되어 폴백 대상.
        return Jsoup.parse("<html><head></head><body><div id=\"root\"></div></body></html>", URL);
    }

    private FallbackHtmlFetcher fetcher(HtmlFetcher jsoup, HtmlFetcher crawler, boolean enabled) {
        return new FallbackHtmlFetcher(jsoup, crawler, enabled, 200);
    }

    @Test
    void jsoup_결과가_충분하면_크롤러를_부르지_않는다() {
        AtomicInteger crawlerCalls = new AtomicInteger();
        HtmlFetcher jsoup = url -> richDoc();
        HtmlFetcher crawler = url -> {
            crawlerCalls.incrementAndGet();
            return richDoc();
        };

        Document result = fetcher(jsoup, crawler, true).fetch(URL);

        assertThat(result.selectFirst("meta[property=og:title]")).isNotNull();
        assertThat(crawlerCalls.get()).isZero();
    }

    @Test
    void jsoup_결과가_빈약하면_크롤러로_폴백한다() {
        AtomicInteger crawlerCalls = new AtomicInteger();
        HtmlFetcher jsoup = url -> emptyShell();
        HtmlFetcher crawler = url -> {
            crawlerCalls.incrementAndGet();
            return Jsoup.parse("<html><body><p>크롤러가 렌더한 본문</p></body></html>", URL);
        };

        Document result = fetcher(jsoup, crawler, true).fetch(URL);

        assertThat(crawlerCalls.get()).isEqualTo(1);
        assertThat(result.body().text()).contains("크롤러가 렌더한 본문");
    }

    @Test
    void jsoup이_예외로_실패하면_크롤러로_폴백한다() {
        HtmlFetcher jsoup = url -> {
            throw new HtmlFetchException("403 차단");
        };
        HtmlFetcher crawler = url -> Jsoup.parse("<html><body><p>우회 성공</p></body></html>", URL);

        Document result = fetcher(jsoup, crawler, true).fetch(URL);

        assertThat(result.body().text()).contains("우회 성공");
    }

    @Test
    void 크롤러도_실패하면_jsoup이_받아둔_문서를_그대로_쓴다() {
        HtmlFetcher jsoup = url -> emptyShell();
        HtmlFetcher crawler = url -> {
            throw new HtmlFetchException("크롤러 다운");
        };

        Document result = fetcher(jsoup, crawler, true).fetch(URL);

        // 빈약하더라도 있는 걸 준다(best-effort).
        assertThat(result.selectFirst("#root")).isNotNull();
    }

    @Test
    void jsoup도_크롤러도_실패하면_원래_jsoup_예외를_던진다() {
        HtmlFetcher jsoup = url -> {
            throw new HtmlFetchException("원본 실패");
        };
        HtmlFetcher crawler = url -> {
            throw new HtmlFetchException("폴백도 실패");
        };

        assertThatThrownBy(() -> fetcher(jsoup, crawler, true).fetch(URL))
                .isInstanceOf(HtmlFetchException.class)
                .hasMessageContaining("원본 실패");
    }

    @Test
    void 크롤러가_꺼져있으면_빈약해도_폴백하지_않는다() {
        AtomicInteger crawlerCalls = new AtomicInteger();
        HtmlFetcher jsoup = url -> emptyShell();
        HtmlFetcher crawler = url -> {
            crawlerCalls.incrementAndGet();
            return richDoc();
        };

        Document result = fetcher(jsoup, crawler, false).fetch(URL);

        assertThat(crawlerCalls.get()).isZero();
        assertThat(result.selectFirst("#root")).isNotNull();
    }

    @Test
    void 크롤러가_꺼져있고_jsoup이_실패하면_그대로_예외를_던진다() {
        HtmlFetcher jsoup = url -> {
            throw new HtmlFetchException("꺼진채 실패");
        };
        HtmlFetcher crawler = url -> richDoc();

        assertThatThrownBy(() -> fetcher(jsoup, crawler, false).fetch(URL))
                .isInstanceOf(HtmlFetchException.class)
                .hasMessageContaining("꺼진채 실패");
    }
}
