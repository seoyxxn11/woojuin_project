package com.ssafy.woojuin.domain.item.processing.url;

import net.dankito.readability4j.Readability4J;
import net.dankito.readability4j.Article;
import org.jsoup.nodes.Document;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * 트랙 B — AI가 요약·분류할 실제 본문 텍스트를 확보한다. 트랙 A가 이미 받아둔
 * Document를 재활용하므로 네트워크를 다시 타지 않는다.
 *
 * <p>readability4j로 기사 본문만 뽑아낸다(광고·네비·댓글 제거). 결과가 너무 짧으면
 * 추출에 실패한 것으로 본다 — 목록 페이지·로그인 벽·JS 렌더링 페이지 등은 의미 있는
 * 본문이 안 나오는데, 그런 껍데기를 AI에 넘기면 엉뚱한 분류가 나오기 때문이다.
 */
@Component
public class ContentExtractor {

    private final int minLength;

    public ContentExtractor(@Value("${woojuin.content.min-length:200}") int minLength) {
        this.minLength = minLength;
    }

    /**
     * @return 추출된 본문. 확보 실패(너무 짧거나 없음)면 null — 호출부는 트랙 B 실패로 처리한다.
     */
    public String extract(Document doc) {
        try {
            // readability4j는 자체적으로 DOM을 변형하므로 원본 Document(트랙 A와 공유)를
            // 건드리지 않도록 복제본을 넘긴다.
            Readability4J readability = new Readability4J(doc.baseUri(), doc.clone());
            Article article = readability.parse();
            String text = article.getTextContent();
            if (text == null) {
                return null;
            }
            String normalized = text.replaceAll("\\s+", " ").trim();
            return normalized.length() >= minLength ? normalized : null;
        } catch (Exception e) {
            // 추출 실패가 트랙 A(이미 확보한 미리보기)나 컨슈머 재시도에 영향 주면 안 된다.
            return null;
        }
    }
}
