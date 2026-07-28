package com.ssafy.woojuin.domain.item.processing.url;

import org.jsoup.nodes.Document;

/**
 * URL을 받아 파싱된 HTML 문서를 돌려준다. 트랙 A(OG 스크래핑)와 트랙 B(본문 추출)가
 * <b>같은 Document를 공유</b>하도록 fetch를 한 곳으로 모으는 진입점이다 — 한 URL을
 * 두 번 받아오지 않게 한다.
 *
 * <p>인터페이스로 둔 이유: 실제 네트워크 없이 테스트에서 픽스처 Document를 주입하기 위함.
 * 또한 SSRF 방어·타임아웃·크기 상한 같은 정책을 구현체 한 곳에 가둔다.
 */
public interface HtmlFetcher {

    /**
     * @throws HtmlFetchException 네트워크 실패, 차단된 주소(SSRF), HTML이 아닌 응답,
     *                            크기 초과 등 — 호출부는 트랙 A/B 실패로 처리한다.
     */
    Document fetch(String url);
}
