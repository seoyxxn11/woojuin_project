package com.ssafy.woojuin.domain.item.processing.url;

/** HTML fetch 실패. 트랙 A/B가 이 예외를 잡아 "확보 실패"로 처리한다(재시도 유발 X). */
public class HtmlFetchException extends RuntimeException {

    public HtmlFetchException(String message) {
        super(message);
    }

    public HtmlFetchException(String message, Throwable cause) {
        super(message, cause);
    }
}
