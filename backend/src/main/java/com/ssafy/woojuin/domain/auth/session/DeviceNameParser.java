package com.ssafy.woojuin.domain.auth.session;

/**
 * User-Agent 를 사람이 읽을 기기 이름("Windows · Chrome" 수준)으로 바꾼다.
 *
 * 서버가 해석하는 이유: 클라이언트가 기기 id·이름을 만들어 보내게 하면 모든 클라이언트
 * (웹·익스텐션·Wear OS)를 고쳐야 한다. UA 해석이면 클라이언트 변경이 0 이다.
 *
 * 라이브러리를 쓰지 않는 이유: 기기 목록에 필요한 건 "PC 인지 폰인지, 어느 브라우저인지"
 * 수준이다. UA 파싱 라이브러리는 수천 패턴을 들고 오는데 그 정밀도가 여기선 쓸모가 없다.
 * 못 알아보면 "알 수 없는 기기"로 두는 게 맞는 동작이다.
 */
public final class DeviceNameParser {

    private static final String UNKNOWN = "알 수 없는 기기";

    private DeviceNameParser() {
    }

    public static String parse(String userAgent) {
        if (userAgent == null || userAgent.isBlank()) return UNKNOWN;

        // 우리 워치 앱은 UA 를 직접 정한다(브라우저가 아니라 OS·브라우저 토큰이 없다) —
        // 문구는 서버에 있으므로 워치 출시 후에도 서버 배포만으로 바꿀 수 있다 (S15P11C105-458)
        if (userAgent.contains("Woojuin-WearOS")) return "Wear OS 워치";

        // 크롬 익스텐션도 링크 코드로 자체 세션을 만든다(S15P11C105-498). 브라우저 UA 그대로면
        // 웹 세션과 구분이 안 되므로 poll 요청에만 이 토큰을 실어 보낸다 — 크롬은 fetch 에서
        // User-Agent 재정의를 허용한다(스펙에서 금지 헤더 목록에서 빠졌다).
        if (userAgent.contains("Woojuin-Extension")) return "크롬 익스텐션";

        String os = os(userAgent);
        String browser = browser(userAgent);
        if (os == null && browser == null) return UNKNOWN;
        if (os == null) return browser;
        if (browser == null) return os;
        return os + " · " + browser;
    }

    private static String os(String ua) {
        // 순서가 중요하다 — iPad UA 에도 "Mobile" 이, 안드로이드 UA 에도 "Linux" 가 들어 있다
        if (ua.contains("iPhone")) return "iPhone";
        if (ua.contains("iPad")) return "iPad";
        if (ua.contains("Android")) return "Android";
        if (ua.contains("Windows")) return "Windows";
        if (ua.contains("Macintosh") || ua.contains("Mac OS X")) return "Mac";
        if (ua.contains("Linux")) return "Linux";
        return null;
    }

    private static String browser(String ua) {
        // 파생 브라우저가 원본 토큰을 같이 싣는다 — Edge 는 "Chrome" 을, Chrome 은 "Safari" 를
        // 포함하므로 구체적인 것부터 본다
        if (ua.contains("Edg/") || ua.contains("EdgA/")) return "Edge";
        if (ua.contains("SamsungBrowser/")) return "Samsung Internet";
        if (ua.contains("Firefox/")) return "Firefox";
        if (ua.contains("Chrome/") || ua.contains("CriOS/")) return "Chrome";
        if (ua.contains("Safari/")) return "Safari";
        return null;
    }
}
