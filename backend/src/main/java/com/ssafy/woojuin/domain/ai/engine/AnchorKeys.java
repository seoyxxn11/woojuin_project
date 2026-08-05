package com.ssafy.woojuin.domain.ai.engine;

import java.util.regex.Pattern;

/**
 * 앵커 정규화 키 유틸. AI 서버(category_service.normalize_anchor_key)와 같은 규칙 —
 * 한글/영문/숫자만 남기고 소문자로 이어 붙인다. 매칭·Redis 키에 쓴다.
 */
public final class AnchorKeys {

    private static final Pattern TOKEN = Pattern.compile("[가-힣a-zA-Z0-9]+");

    private AnchorKeys() {
    }

    public static String normalize(String name) {
        if (name == null || name.isBlank()) {
            return "";
        }
        StringBuilder sb = new StringBuilder();
        var matcher = TOKEN.matcher(name.toLowerCase());
        while (matcher.find()) {
            sb.append(matcher.group());
        }
        return sb.toString();
    }
}
