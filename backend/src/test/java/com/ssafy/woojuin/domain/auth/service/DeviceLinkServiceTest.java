package com.ssafy.woojuin.domain.auth.service;

import com.ssafy.woojuin.domain.auth.dto.DeviceLinkPollResponse;
import com.ssafy.woojuin.domain.auth.dto.DeviceLinkStartResponse;
import com.ssafy.woojuin.domain.auth.jwt.JwtTokenProvider;
import com.ssafy.woojuin.domain.auth.repository.UserRepository;
import com.ssafy.woojuin.domain.auth.session.DeviceLinkStore;
import com.ssafy.woojuin.domain.auth.session.DeviceNameParser;
import com.ssafy.woojuin.domain.auth.session.UserSession;
import com.ssafy.woojuin.domain.auth.session.UserSessionStore;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class DeviceLinkServiceTest {

    private static final String WATCH_UA = "Woojuin-WearOS/1.0";

    @Mock
    private DeviceLinkStore linkStore;

    @Mock
    private UserSessionStore sessionStore;

    @Mock
    private JwtTokenProvider jwtTokenProvider;

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private DeviceLinkService deviceLinkService;

    @Test
    @DisplayName("start 는 코드와 유효 시간을 준다 — 워치 화면에 그대로 뜬다")
    void start_returnsCodeAndTtl() {
        when(linkStore.create()).thenReturn("AB23CD");

        DeviceLinkStartResponse response = deviceLinkService.start();

        assertThat(response.code()).isEqualTo("AB23CD");
        assertThat(response.expiresInSeconds()).isEqualTo(DeviceLinkStore.PENDING_TTL.toSeconds());
    }

    @Test
    @DisplayName("approve 는 만료·오타 코드를 400 으로 거른다")
    void approve_invalidCode_throws() {
        when(linkStore.approve("XXXXXX", 1L)).thenReturn(false);

        assertThatThrownBy(() -> deviceLinkService.approve(1L, "XXXXXX"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    @DisplayName("승인 전 poll 은 PENDING — 세션을 만들지 않는다")
    void poll_pending_returnsPendingWithoutSession() {
        when(linkStore.find("AB23CD")).thenReturn(Optional.of(pendingState()));

        DeviceLinkPollResponse response = deviceLinkService.poll("AB23CD", WATCH_UA, null);

        assertThat(response.status()).isEqualTo(DeviceLinkPollResponse.Status.PENDING);
        assertThat(response.accessToken()).isNull();
        verify(sessionStore, never()).save(any(), any());
    }

    @Test
    @DisplayName("승인된 poll 은 코드를 소비하고 로그인과 같은 규칙으로 세션을 만든다")
    void poll_approved_consumesAndCreatesSession() {
        when(linkStore.find("AB23CD")).thenReturn(Optional.of(approvedState(1L)));
        when(userRepository.existsByIdAndDeletedAtIsNull(1L)).thenReturn(true);
        when(jwtTokenProvider.createAccessToken(eq(1L), anyString())).thenReturn("access-token");
        when(jwtTokenProvider.createRefreshToken(eq(1L), anyString())).thenReturn("refresh-token");

        DeviceLinkPollResponse response = deviceLinkService.poll("AB23CD", WATCH_UA, null);

        assertThat(response.status()).isEqualTo(DeviceLinkPollResponse.Status.APPROVED);
        assertThat(response.accessToken()).isEqualTo("access-token");
        assertThat(response.refreshToken()).isEqualTo("refresh-token");
        verify(linkStore).consume("AB23CD");

        // 토큰의 sid 와 저장된 세션의 sid 가 같아야 refresh·기기 해제가 세션을 찾는다
        ArgumentCaptor<UserSession> saved = ArgumentCaptor.forClass(UserSession.class);
        ArgumentCaptor<String> sid = ArgumentCaptor.forClass(String.class);
        verify(sessionStore).save(eq(1L), saved.capture());
        verify(jwtTokenProvider).createAccessToken(eq(1L), sid.capture());
        assertThat(saved.getValue().sid()).isEqualTo(sid.getValue());
        assertThat(saved.getValue().userAgent()).isEqualTo(WATCH_UA);
        assertThat(saved.getValue().refreshToken()).isEqualTo("refresh-token");
    }

    @Test
    @DisplayName("client 표식이 오면 UA 앞에 붙는다 — 기기 목록이 익스텐션을 알아보는 근거 (S15P11C105-498)")
    void poll_withClient_prependsToUserAgent() {
        // 크롬은 fetch 의 User-Agent 재정의를 조용히 무시한다(실측). 브라우저 안에서 도는
        // 클라이언트는 본문의 client 로 자신을 밝히고, 서버가 UA 앞에 붙여 세션에 남긴다.
        when(linkStore.find("AB23CD")).thenReturn(Optional.of(approvedState(1L)));
        when(userRepository.existsByIdAndDeletedAtIsNull(1L)).thenReturn(true);
        when(jwtTokenProvider.createAccessToken(eq(1L), anyString())).thenReturn("access-token");
        when(jwtTokenProvider.createRefreshToken(eq(1L), anyString())).thenReturn("refresh-token");

        deviceLinkService.poll("AB23CD", "Mozilla/5.0 (Windows NT 10.0)", "Woojuin-Extension/1.0");

        ArgumentCaptor<UserSession> saved = ArgumentCaptor.forClass(UserSession.class);
        verify(sessionStore).save(eq(1L), saved.capture());
        assertThat(saved.getValue().userAgent())
                .isEqualTo("Woojuin-Extension/1.0 Mozilla/5.0 (Windows NT 10.0)");
        assertThat(DeviceNameParser.parse(saved.getValue().userAgent())).isEqualTo("크롬 익스텐션");
    }

    @Test
    @DisplayName("만료·미발급 코드의 poll 은 400 — 워치는 새 코드를 발급받는다")
    void poll_unknownCode_throws() {
        when(linkStore.find("EXPIRED")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> deviceLinkService.poll("EXPIRED", WATCH_UA, null))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    @DisplayName("승인과 소비 사이에 탈퇴한 계정은 거부하고 코드를 소비한다")
    void poll_withdrawnUser_throwsAndConsumes() {
        when(linkStore.find("AB23CD")).thenReturn(Optional.of(approvedState(1L)));
        when(userRepository.existsByIdAndDeletedAtIsNull(1L)).thenReturn(false);

        assertThatThrownBy(() -> deviceLinkService.poll("AB23CD", WATCH_UA, null))
                .isInstanceOf(IllegalArgumentException.class);

        verify(linkStore).consume("AB23CD");
        verify(sessionStore, never()).save(any(), any());
    }

    private DeviceLinkStore.LinkState pendingState() {
        return new DeviceLinkStore.LinkState(false, null);
    }

    private DeviceLinkStore.LinkState approvedState(Long userId) {
        return new DeviceLinkStore.LinkState(true, userId);
    }
}
