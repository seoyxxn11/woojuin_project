package com.ssafy.woojuin.domain.item.processing.url;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.net.URI;
import org.junit.jupiter.api.Test;

/**
 * 리터럴 IP를 쓰면 DNS 조회 없이 검증되므로 네트워크 없이 테스트할 수 있다.
 * (InetAddress.getAllByName은 IP 리터럴을 그대로 파싱한다)
 */
class PrivateNetworkGuardTest {

    private final PrivateNetworkGuard guard = new PrivateNetworkGuard();

    @Test
    void 공인_IP는_허용한다() {
        assertThatCode(() -> guard.verifyAllowed(URI.create("https://8.8.8.8/path")))
                .doesNotThrowAnyException();
    }

    @Test
    void 루프백을_차단한다() {
        assertThatThrownBy(() -> guard.verifyAllowed(URI.create("http://127.0.0.1/")))
                .isInstanceOf(HtmlFetchException.class);
    }

    @Test
    void 사설대역을_차단한다() {
        assertThatThrownBy(() -> guard.verifyAllowed(URI.create("http://10.0.0.5/")))
                .isInstanceOf(HtmlFetchException.class);
        assertThatThrownBy(() -> guard.verifyAllowed(URI.create("http://192.168.1.1/")))
                .isInstanceOf(HtmlFetchException.class);
        assertThatThrownBy(() -> guard.verifyAllowed(URI.create("http://172.16.0.1/")))
                .isInstanceOf(HtmlFetchException.class);
    }

    @Test
    void AWS_메타데이터_링크로컬_주소를_차단한다() {
        assertThatThrownBy(() -> guard.verifyAllowed(URI.create("http://169.254.169.254/latest/meta-data/")))
                .isInstanceOf(HtmlFetchException.class);
    }

    @Test
    void http_https가_아닌_scheme을_차단한다() {
        assertThatThrownBy(() -> guard.verifyAllowed(URI.create("file:///etc/passwd")))
                .isInstanceOf(HtmlFetchException.class);
        assertThatThrownBy(() -> guard.verifyAllowed(URI.create("ftp://8.8.8.8/x")))
                .isInstanceOf(HtmlFetchException.class);
    }
}
