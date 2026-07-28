package com.ssafy.woojuin.domain.auth.oauth;

import java.util.Map;

/**
 * OidcUser.getClaims()로 얻은 구글 클레임을 우리 도메인 필드로 변환한다.
 */
public class GoogleUserInfo {

    private final Map<String, Object> attributes;

    public GoogleUserInfo(Map<String, Object> attributes) {
        this.attributes = attributes;
    }

    public String getProviderId() {
        return String.valueOf(attributes.get("sub"));
    }

    public String getEmail() {
        return (String) attributes.get("email");
    }

    public String getNickname() {
        return (String) attributes.get("name");
    }
}
