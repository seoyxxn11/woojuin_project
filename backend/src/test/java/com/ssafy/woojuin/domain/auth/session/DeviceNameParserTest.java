package com.ssafy.woojuin.domain.auth.session;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

import static org.assertj.core.api.Assertions.assertThat;

class DeviceNameParserTest {

    @ParameterizedTest(name = "{1}")
    @DisplayName("실제 UA 문자열이 기기 이름으로 바뀐다")
    @CsvSource(delimiter = '|', value = {
            // 실기기에서 수집한 형태의 UA — 순서 민감 케이스(파생 브라우저·모바일 OS)를 위주로
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 | Windows · Chrome",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0 | Windows · Edge",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15 | Mac · Safari",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1 | iPhone · Safari",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/126.0.6478.54 Mobile/15E148 Safari/604.1 | iPhone · Chrome",
            "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1 | iPad · Safari",
            "Mozilla/5.0 (Linux; Android 14; SM-S921N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36 | Android · Chrome",
            "Mozilla/5.0 (Linux; Android 14; SM-S921N) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/25.0 Chrome/121.0.0.0 Mobile Safari/537.36 | Android · Samsung Internet",
            "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0 | Linux · Firefox",
    })
    void parse_realUserAgents(String userAgent, String expected) {
        assertThat(DeviceNameParser.parse(userAgent)).isEqualTo(expected);
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {"   ", "curl/8.7.1"})
    @DisplayName("UA 가 없거나 알아볼 수 없으면 '알 수 없는 기기'")
    void parse_unknownUserAgents(String userAgent) {
        assertThat(DeviceNameParser.parse(userAgent)).isEqualTo("알 수 없는 기기");
    }

    @Test
    @DisplayName("OS 만 알아봐도 그것만 보여준다 — 절반의 정보가 '알 수 없음'보다 낫다")
    void parse_osOnly() {
        assertThat(DeviceNameParser.parse("Mozilla/5.0 (Windows NT 10.0; Win64; x64)"))
                .isEqualTo("Windows");
    }

    @Test
    @DisplayName("우리 워치 앱의 UA 는 워치임을 알아볼 수 있는 이름이 된다 (S15P11C105-458)")
    void parse_wearOsApp() {
        assertThat(DeviceNameParser.parse("Woojuin-WearOS/1.0")).isEqualTo("Wear OS 워치");
    }

    @Test
    @DisplayName("크롬 익스텐션의 링크 poll UA 는 익스텐션임을 알아볼 수 있는 이름이 된다 (S15P11C105-498)")
    void parse_extension() {
        assertThat(DeviceNameParser.parse("Woojuin-Extension/1.0")).isEqualTo("크롬 익스텐션");
    }
}
