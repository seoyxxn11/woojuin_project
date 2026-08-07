package com.ssafy.woojuin.domain.auth.service;

import com.ssafy.woojuin.domain.auth.dto.DeviceLinkPollResponse;
import com.ssafy.woojuin.domain.auth.dto.DeviceLinkStartResponse;
import com.ssafy.woojuin.domain.auth.jwt.JwtTokenProvider;
import com.ssafy.woojuin.domain.auth.repository.UserRepository;
import com.ssafy.woojuin.domain.auth.session.DeviceLinkStore;
import com.ssafy.woojuin.domain.auth.session.UserSession;
import com.ssafy.woojuin.domain.auth.session.UserSessionStore;
import org.springframework.stereotype.Service;

/**
 * 워치 링크 코드 로그인 (S15P11C105-458) — 브라우저 없는 기기의 로그인.
 *
 * 승인(approve)은 웹의 인증된 사용자가 하고, 토큰은 워치의 poll 이 받아 간다.
 * 발급되는 세션은 다른 기기와 완전히 동일하다(-459) — 기기 목록에 뜨고 거기서 끊긴다.
 */
@Service
public class DeviceLinkService {

    private final DeviceLinkStore linkStore;
    private final UserSessionStore sessionStore;
    private final JwtTokenProvider jwtTokenProvider;
    private final UserRepository userRepository;

    public DeviceLinkService(DeviceLinkStore linkStore, UserSessionStore sessionStore,
                             JwtTokenProvider jwtTokenProvider, UserRepository userRepository) {
        this.linkStore = linkStore;
        this.sessionStore = sessionStore;
        this.jwtTokenProvider = jwtTokenProvider;
        this.userRepository = userRepository;
    }

    /** 워치가 화면에 띄울 코드 발급 — 비인증. 워치는 이 코드로 poll 을 시작한다 */
    public DeviceLinkStartResponse start() {
        return new DeviceLinkStartResponse(
                linkStore.create(), DeviceLinkStore.PENDING_TTL.toSeconds());
    }

    /** 웹(인증됨)에서 워치 화면의 코드를 입력해 승인한다 */
    public void approve(Long userId, String code) {
        if (!linkStore.approve(code, userId)) {
            throw new IllegalArgumentException("코드가 만료되었거나 올바르지 않습니다");
        }
    }

    /**
     * 워치가 승인 여부를 물어본다 — 비인증(아직 토큰이 없는 기기다).
     *
     * 승인 전이면 PENDING 을 돌려주고, 승인됐으면 코드를 소비하며 로그인과 같은 규칙으로
     * 세션을 만든다(sid 발급 + UserSession 저장). 만료·미발급 코드는 400 — 워치는 새
     * 코드를 발급받아 다시 띄운다.
     */
    public DeviceLinkPollResponse poll(String code, String userAgent, String client) {
        DeviceLinkStore.LinkState state = linkStore.find(code)
                .orElseThrow(() -> new IllegalArgumentException("코드가 만료되었거나 올바르지 않습니다"));

        if (!state.approved()) {
            return DeviceLinkPollResponse.pending();
        }

        Long userId = state.userId();
        // 승인과 소비 사이에 탈퇴한 계정을 걸러낸다 — 로그인 경로와 같은 확인
        if (!userRepository.existsByIdAndDeletedAtIsNull(userId)) {
            linkStore.consume(code);
            throw new IllegalArgumentException("사용할 수 없는 계정입니다");
        }

        linkStore.consume(code);

        String sid = UserSession.newSessionId();
        String accessToken = jwtTokenProvider.createAccessToken(userId, sid);
        String refreshToken = jwtTokenProvider.createRefreshToken(userId, sid);
        // client 표식이 오면 UA 앞에 붙인다 — DeviceNameParser 가 표식을 먼저 보므로 기기
        // 목록에 그 이름("크롬 익스텐션")이 뜨고, 원래 UA 는 뒤에 남아 조사할 때 볼 수 있다.
        // 브라우저 안 클라이언트는 fetch 로 UA 를 못 바꿔서 본문으로 밝힌다(DeviceLinkPollRequest).
        String effectiveUserAgent = client == null || client.isBlank()
                ? userAgent
                : (userAgent == null || userAgent.isBlank() ? client : client + " " + userAgent);
        sessionStore.save(userId, UserSession.start(sid, refreshToken, effectiveUserAgent));

        return DeviceLinkPollResponse.approved(accessToken, refreshToken);
    }
}
