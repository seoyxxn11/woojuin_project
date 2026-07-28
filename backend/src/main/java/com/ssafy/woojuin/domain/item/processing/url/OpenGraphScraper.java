package com.ssafy.woojuin.domain.item.processing.url;

import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.springframework.stereotype.Component;

/**
 * 이미 받아온 Document에서 미리보기 메타데이터를 뽑는다. 네트워크를 타지 않는 순수
 * 파싱이라 픽스처 HTML로 단위 테스트할 수 있다.
 *
 * <p>폴백 순서: og:* → twitter:* → 표준 태그(&lt;title&gt;, meta[name=description]).
 * 대부분의 현대 사이트는 og:*를 주지만, 없을 때를 대비해 단계적으로 내려간다.
 */
@Component
public class OpenGraphScraper {

    public UrlPreview scrape(Document doc) {
        String title = firstNonBlank(
                metaContent(doc, "property", "og:title"),
                metaContent(doc, "name", "twitter:title"),
                doc.title());

        String description = firstNonBlank(
                metaContent(doc, "property", "og:description"),
                metaContent(doc, "name", "twitter:description"),
                metaContent(doc, "name", "description"));

        String rawThumb = firstNonBlank(
                metaContent(doc, "property", "og:image"),
                metaContent(doc, "name", "twitter:image"));
        String thumbnail = absolutize(doc, rawThumb);

        return new UrlPreview(title, thumbnail, description);
    }

    private String metaContent(Document doc, String attr, String value) {
        Element el = doc.selectFirst("meta[" + attr + "=" + value + "]");
        return el != null ? el.attr("content") : null;
    }

    /** og:image가 상대경로(/img/thumb.png)로 오는 사이트가 있어 문서 기준으로 절대화한다. */
    private String absolutize(Document doc, String url) {
        if (url == null || url.isBlank()) {
            return null;
        }
        if (url.startsWith("http://") || url.startsWith("https://")) {
            return url;
        }
        try {
            return java.net.URI.create(doc.baseUri()).resolve(url).toString();
        } catch (RuntimeException e) {
            return url;   // 절대화 실패해도 원본이라도 준다
        }
    }

    private String firstNonBlank(String... values) {
        for (String v : values) {
            if (v != null && !v.isBlank()) {
                return v.trim();
            }
        }
        return null;
    }
}
