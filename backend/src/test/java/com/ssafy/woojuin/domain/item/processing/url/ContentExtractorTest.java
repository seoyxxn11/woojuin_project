package com.ssafy.woojuin.domain.item.processing.url;

import static org.assertj.core.api.Assertions.assertThat;

import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.junit.jupiter.api.Test;

class ContentExtractorTest {

    // 테스트에선 짧은 픽스처로도 통과하도록 최소 길이를 낮춘다.
    private final ContentExtractor extractor = new ContentExtractor(50);

    @Test
    void 기사_본문을_추출한다() {
        String body = "우주인은 흩어진 링크와 사진과 메모를 한 곳에 모아 정리해주는 서비스입니다. "
                + "저장은 1초면 끝나고 정리는 AI가 대신합니다. 찾을 때는 검색 한 번이면 됩니다. "
                + "이 문단은 readability가 본문으로 인식할 만큼 충분히 길게 작성되었습니다.";
        Document doc = Jsoup.parse("""
                <html><head><title>소개</title></head><body>
                  <nav>메뉴 홈 로그인</nav>
                  <article><h1>우주인 소개</h1><p>%s</p><p>%s</p></article>
                  <footer>copyright</footer>
                </body></html>
                """.formatted(body, body), "https://example.com/intro");

        String content = extractor.extract(doc);

        assertThat(content).isNotNull();
        assertThat(content).contains("저장은 1초");
    }

    @Test
    void 본문이_너무_짧으면_null을_반환한다() {
        Document doc = Jsoup.parse(
                "<html><head><title>x</title></head><body><p>짧음</p></body></html>",
                "https://example.com/x");

        assertThat(extractor.extract(doc)).isNull();
    }
}
