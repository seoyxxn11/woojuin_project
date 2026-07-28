package com.ssafy.woojuin.domain.item.processing.url;

import java.net.InetAddress;
import java.net.URI;
import java.net.UnknownHostException;
import org.springframework.stereotype.Component;

/**
 * SSRF 방어. 사용자가 준 URL을 서버가 직접 받아오므로, 내부망·클라우드 메타데이터
 * 서버 같은 곳을 향하지 못하게 막는다.
 *
 * <p>호스트를 실제 IP로 해석한 뒤 사설/루프백/링크로컬 대역이면 차단한다. 리다이렉트
 * 되면 최종 목적지가 바뀌므로 <b>홉마다</b> 다시 검사해야 한다(DNS 리바인딩 방어).
 */
@Component
public class PrivateNetworkGuard {

    /** http/https만 허용. file:, gopher:, ftp: 등으로 우회하는 걸 막는다. */
    public void verifyAllowed(URI uri) {
        String scheme = uri.getScheme();
        if (scheme == null || !(scheme.equalsIgnoreCase("http") || scheme.equalsIgnoreCase("https"))) {
            throw new HtmlFetchException("허용되지 않은 scheme: " + scheme);
        }
        String host = uri.getHost();
        if (host == null || host.isBlank()) {
            throw new HtmlFetchException("호스트가 없는 URL: " + uri);
        }

        InetAddress[] addresses;
        try {
            addresses = InetAddress.getAllByName(host);
        } catch (UnknownHostException e) {
            throw new HtmlFetchException("호스트를 해석할 수 없음: " + host, e);
        }
        for (InetAddress address : addresses) {
            if (isBlocked(address)) {
                throw new HtmlFetchException("차단된 내부 주소로의 요청: " + host + " -> " + address.getHostAddress());
            }
        }
    }

    private boolean isBlocked(InetAddress address) {
        return address.isLoopbackAddress()      // 127.0.0.0/8, ::1
                || address.isAnyLocalAddress()   // 0.0.0.0, ::
                || address.isLinkLocalAddress()  // 169.254.0.0/16 (AWS 메타데이터 포함), fe80::/10
                || address.isSiteLocalAddress()  // 10/8, 172.16/12, 192.168/16
                || address.isMulticastAddress()
                || isUniqueLocalIpv6(address);   // fc00::/7
    }

    /** IPv6 사설 대역(fc00::/7)은 InetAddress에 판별 메서드가 없어 첫 바이트로 직접 본다. */
    private boolean isUniqueLocalIpv6(InetAddress address) {
        byte[] bytes = address.getAddress();
        return bytes.length == 16 && (bytes[0] & 0xFE) == 0xFC;
    }
}
