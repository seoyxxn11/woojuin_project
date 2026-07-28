package com.ssafy.woojuin.domain.item.processing.url;

import static org.assertj.core.api.Assertions.assertThat;

import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.junit.jupiter.api.Test;

class OpenGraphScraperTest {

    private final OpenGraphScraper scraper = new OpenGraphScraper();

    private Document parse(String html) {
        // baseUri를 줘야 상대경로 og:image 절대화를 검증할 수 있다.
        return Jsoup.parse(html, "https://example.com/article");
    }

    @Test
    void og_태그를_우선_사용한다() {
        Document doc = parse("""
                <html><head>
                  <title>문서 타이틀</title>
                  <meta property="og:title" content="OG 타이틀">
                  <meta property="og:description" content="OG 설명">
                  <meta property="og:image" content="https://cdn.example.com/thumb.png">
                </head><body></body></html>
                """);

        UrlPreview preview = scraper.scrape(doc);

        assertThat(preview.title()).isEqualTo("OG 타이틀");
        assertThat(preview.description()).isEqualTo("OG 설명");
        assertThat(preview.thumbnailUrl()).isEqualTo("https://cdn.example.com/thumb.png");
    }

    @Test
    void og가_없으면_twitter_그다음_표준태그로_폴백한다() {
        Document doc = parse("""
                <html><head>
                  <title>문서 타이틀</title>
                  <meta name="twitter:title" content="트위터 타이틀">
                  <meta name="description" content="표준 설명">
                </head><body></body></html>
                """);

        UrlPreview preview = scraper.scrape(doc);

        assertThat(preview.title()).isEqualTo("트위터 타이틀");
        assertThat(preview.description()).isEqualTo("표준 설명");
    }

    @Test
    void og도_twitter도_없으면_title태그를_쓴다() {
        Document doc = parse("<html><head><title>문서 타이틀</title></head><body></body></html>");

        UrlPreview preview = scraper.scrape(doc);

        assertThat(preview.title()).isEqualTo("문서 타이틀");
        assertThat(preview.thumbnailUrl()).isNull();
    }

    @Test
    void 상대경로_og_image를_절대경로로_바꾼다() {
        Document doc = parse("""
                <html><head>
                  <meta property="og:title" content="T">
                  <meta property="og:image" content="/img/thumb.png">
                </head><body></body></html>
                """);

        UrlPreview preview = scraper.scrape(doc);

        assertThat(preview.thumbnailUrl()).isEqualTo("https://example.com/img/thumb.png");
    }

    @Test
    void 메타가_전혀_없으면_hasNothing이_true다() {
        Document doc = parse("<html><head></head><body>본문만</body></html>");

        assertThat(scraper.scrape(doc).hasNothing()).isTrue();
    }
}
