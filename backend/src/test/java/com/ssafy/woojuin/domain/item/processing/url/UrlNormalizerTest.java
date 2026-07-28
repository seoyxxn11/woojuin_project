package com.ssafy.woojuin.domain.item.processing.url;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class UrlNormalizerTest {

    private final UrlNormalizer normalizer = new UrlNormalizer();

    @Test
    void utm_추적_파라미터를_제거한다() {
        String result = normalizer.normalize(
                "https://example.com/post?id=10&utm_source=news&utm_medium=email");

        assertThat(result).isEqualTo("https://example.com/post?id=10");
    }

    @Test
    void 알려진_추적_키와_fragment를_제거한다() {
        String result = normalizer.normalize("https://example.com/a?fbclid=xyz#section");

        assertThat(result).isEqualTo("https://example.com/a");
    }

    @Test
    void youtu_be_단축링크를_watch_형태로_바꾼다() {
        String result = normalizer.normalize("https://youtu.be/dQw4w9WgXcQ");

        assertThat(result).isEqualTo("https://www.youtube.com/watch?v=dQw4w9WgXcQ");
    }

    @Test
    void 네이버블로그_iframe을_실제_포스트_URL로_바꾼다() {
        String result = normalizer.normalize(
                "https://blog.naver.com/PostView.naver?blogId=woojuin&logNo=223");

        assertThat(result).isEqualTo("https://blog.naver.com/woojuin/223");
    }

    @Test
    void 모바일_호스트를_데스크톱으로_바꾼다() {
        String result = normalizer.normalize("https://m.example.com/path?q=1");

        assertThat(result).isEqualTo("https://example.com/path?q=1");
    }

    @Test
    void 정규화할것이_없으면_원본을_유지한다() {
        String url = "https://example.com/clean";
        assertThat(normalizer.normalize(url)).isEqualTo(url);
    }

    @Test
    void 파싱_불가능한_입력은_원본을_그대로_반환한다() {
        String bad = "not a url ::: %%%";
        assertThat(normalizer.normalize(bad)).isEqualTo(bad);
    }
}
