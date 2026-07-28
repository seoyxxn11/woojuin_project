package com.ssafy.woojuin.domain.item.processing.url;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.springframework.stereotype.Component;

/**
 * 저장된 URL을 스크래핑하기 좋은 형태로 정규화한다.
 *
 * <ul>
 *   <li>추적 파라미터(utm_*, fbclid, gclid 등) 제거 — 같은 문서가 다른 URL로 저장되는 걸 줄이고
 *       oEmbed 매칭 정확도를 높인다</li>
 *   <li>youtu.be 단축 → youtube.com/watch?v= (oEmbed 제공자 매칭)</li>
 *   <li>모바일 호스트(m.blog.naver.com 등) → 데스크톱 호스트 (OG 태그가 더 잘 붙는다)</li>
 *   <li>네이버 블로그 iframe(PostView.naver) → 실제 포스트 URL</li>
 * </ul>
 *
 * <p>정규화가 불가능하거나 파싱이 실패하면 <b>원본을 그대로 반환</b>한다 — 정규화는
 * 최선 노력일 뿐, 여기서 아이템 처리를 실패시키면 안 된다.
 */
@Component
public class UrlNormalizer {

    private static final List<String> TRACKING_PREFIXES = List.of("utm_");
    private static final List<String> TRACKING_KEYS = List.of(
            "fbclid", "gclid", "igshid", "mc_cid", "mc_eid", "spm", "ref", "ref_src");

    public String normalize(String rawUrl) {
        if (rawUrl == null || rawUrl.isBlank()) {
            return rawUrl;
        }
        try {
            URI uri = new URI(rawUrl.trim());
            uri = rewriteHostSpecific(uri);
            String cleanedQuery = stripTracking(uri.getQuery());
            URI result = new URI(
                    uri.getScheme(), uri.getAuthority(), uri.getPath(),
                    cleanedQuery, null);   // fragment 제거 (#앵커는 문서 동일)
            return result.toString();
        } catch (URISyntaxException e) {
            return rawUrl;
        }
    }

    /** 유튜브 단축·모바일 호스트·네이버 블로그처럼 호스트별로 형태가 정해진 케이스를 바로잡는다. */
    private URI rewriteHostSpecific(URI uri) throws URISyntaxException {
        String host = uri.getHost();
        if (host == null) {
            return uri;
        }
        host = host.toLowerCase(Locale.ROOT);

        // youtu.be/{id} → youtube.com/watch?v={id}
        if (host.equals("youtu.be")) {
            String id = trimLeadingSlash(uri.getPath());
            if (!id.isBlank()) {
                return new URI("https", "www.youtube.com", "/watch", "v=" + id, null);
            }
        }

        // 네이버 블로그 iframe: blog.naver.com/PostView.naver?blogId=X&logNo=Y
        //   → blog.naver.com/{blogId}/{logNo} (OG 태그가 붙는 실제 포스트)
        if (host.endsWith("blog.naver.com") && uri.getPath() != null
                && uri.getPath().contains("PostView")) {
            String blogId = queryValue(uri.getQuery(), "blogId");
            String logNo = queryValue(uri.getQuery(), "logNo");
            if (blogId != null && logNo != null) {
                return new URI("https", "blog.naver.com", "/" + blogId + "/" + logNo, null, null);
            }
        }

        // m.* 모바일 호스트 → 데스크톱 호스트
        if (host.startsWith("m.")) {
            return new URI(uri.getScheme(), uri.getUserInfo(), host.substring(2),
                    uri.getPort(), uri.getPath(), uri.getQuery(), uri.getFragment());
        }

        return uri;
    }

    private String stripTracking(String query) {
        if (query == null || query.isBlank()) {
            return null;
        }
        List<String> kept = new ArrayList<>();
        for (String param : query.split("&")) {
            String key = param.contains("=") ? param.substring(0, param.indexOf('=')) : param;
            String lower = key.toLowerCase(Locale.ROOT);
            boolean tracking = TRACKING_KEYS.contains(lower)
                    || TRACKING_PREFIXES.stream().anyMatch(lower::startsWith);
            if (!tracking) {
                kept.add(param);
            }
        }
        return kept.isEmpty() ? null : String.join("&", kept);
    }

    private String queryValue(String query, String key) {
        if (query == null) {
            return null;
        }
        for (String param : query.split("&")) {
            int eq = param.indexOf('=');
            if (eq > 0 && param.substring(0, eq).equalsIgnoreCase(key)) {
                return param.substring(eq + 1);
            }
        }
        return null;
    }

    private String trimLeadingSlash(String path) {
        if (path == null) {
            return "";
        }
        return path.startsWith("/") ? path.substring(1) : path;
    }
}
