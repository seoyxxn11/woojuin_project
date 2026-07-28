package com.ssafy.woojuin.domain.auth.oauth;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class GoogleUserInfoTest {

    @Test
    @DisplayName("구글 OIDC 클레임(sub/email/name)에서 필드를 추출한다")
    void extractsFieldsFromClaims() {
        Map<String, Object> attributes = Map.of(
                "sub", "google-456",
                "email", "test@google.com",
                "name", "우주인"
        );

        GoogleUserInfo userInfo = new GoogleUserInfo(attributes);

        assertThat(userInfo.getProviderId()).isEqualTo("google-456");
        assertThat(userInfo.getEmail()).isEqualTo("test@google.com");
        assertThat(userInfo.getNickname()).isEqualTo("우주인");
    }
}
