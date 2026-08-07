import { publicApiFetch, WEB_ORIGIN } from '@/api/client';
import { saveTokens } from '@/storage/authStorage';

/**
 * 링크 코드(device-link) 로그인 — 워치(S15P11C105-458)와 같은 흐름의 익스텐션판(-498).
 *
 * 예전의 "웹 세션 물려받기"를 대체한다. 물려받기는 웹과 서버 세션을 공유해서 로그아웃이
 * 예측 불가능하게 얽혔다 — 확장에서 로그아웃해도 웹 세션이 살아 있으면 로그인 버튼만으로
 * 복귀했고, 웹에서 재로그인하면 세션이 갈라져 웹 로그아웃이 확장에 아무 영향이 없었다.
 * 링크 코드는 **확장 전용 세션**을 만들므로 이 계층이 통째로 사라진다: 폰/PC처럼 기기
 * 독립이고, 마이페이지 기기 목록에 "크롬 익스텐션"으로 떠서 원격으로 끊을 수도 있다.
 *
 * 흐름: 코드 발급 → 승인 창(`/my?linkCode=`) 열기 → 여기서 폴링 → 승인되면 토큰 저장.
 * 팝업이 아니라 **백그라운드가 부른다** — 승인 창이 포커스를 가져가는 순간 팝업은 닫혀서
 * 폴링을 이어갈 수 없다.
 */

interface DeviceLinkStart {
  code: string;
  expiresInSeconds: number;
}

interface DeviceLinkPoll {
  status: 'PENDING' | 'APPROVED';
  accessToken?: string;
  refreshToken?: string;
}

/** 승인 창의 windowId. 서비스워커는 언제든 죽을 수 있어 메모리 대신 storage 에 둔다. */
const LINK_WINDOW_KEY = 'loginWindowId';

const POLL_INTERVAL_MS = 2_000;

/**
 * 진행 중인 폴링의 식별자. 로그인 버튼을 연달아 누르면(팝업을 닫았다 다시 열어서) 흐름이
 * 여러 개 돌 수 있는데, 마지막 것만 살리고 나머지는 다음 턴에서 스스로 멈춘다.
 * 서비스워커가 죽으면 같이 사라지지만, 폴링 fetch 가 유휴 타이머를 계속 밀어내므로
 * 코드 수명(몇 분) 동안은 살아 있다 — 죽으면 사용자가 로그인을 다시 누르면 된다.
 */
let activeFlow = 0;

/**
 * 로그인 흐름 전체를 진행한다. 반환은 **창을 연 직후** — 승인은 몇 분이 걸릴 수 있어
 * 호출자(팝업)가 기다릴 수 없고, 결과는 storage 의 토큰 변화로 전달된다(팝업이 듣는다).
 *
 * @throws 코드 발급 실패(통신 없음 등). 창이 열리기 전이므로 팝업이 받아서 보여줄 수 있다.
 */
export async function beginDeviceLinkLogin(): Promise<void> {
  const started = await publicApiFetch<DeviceLinkStart>('/auth/device-link', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  const window = await chrome.windows.create({
    // 마이페이지가 linkCode 쿼리를 보고 승인 모달을 코드가 채워진 채로 연다.
    // 웹에 로그인돼 있지 않으면 로그인 화면부터 — postLoginRedirect 가 쿼리째 돌려보낸다.
    url: `${WEB_ORIGIN}/my?linkCode=${started.code}`,
    type: 'popup',
    width: 460,
    height: 760,
    focused: true,
  });
  if (window.id !== undefined) {
    await chrome.storage.local.set({ [LINK_WINDOW_KEY]: window.id });
  }

  const flow = ++activeFlow;
  void pollUntilApproved(flow, started);
}

async function pollUntilApproved(flow: number, started: DeviceLinkStart): Promise<void> {
  const deadline = Date.now() + started.expiresInSeconds * 1_000;
  while (Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    if (flow !== activeFlow) return; // 더 새 흐름이 시작됐다 — 이 코드는 버려졌다

    let result: DeviceLinkPoll;
    try {
      result = await publicApiFetch<DeviceLinkPoll>('/auth/device-link/poll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // client 가 세션 이름의 근거 — DeviceNameParser 가 이 표식을 보고 "크롬 익스텐션"
        // 으로 표기한다(워치의 Woojuin-WearOS UA 와 같은 패턴). 헤더가 아니라 본문인 이유:
        // 크롬이 fetch 의 User-Agent 재정의를 조용히 무시한다(2026-08-07 실측 — 헤더에
        // 실었더니 세션에 브라우저 UA 가 찍혔다).
        body: JSON.stringify({ code: started.code, client: 'Woojuin-Extension/1.0' }),
      });
    } catch {
      // 코드 만료·소비는 400 으로 온다 — 흐름을 접는다. 사용자는 로그인을 다시 누른다.
      // (일시적 통신 오류도 접히지만, 다음 클릭이 새 코드라 복구 경로는 같다)
      return;
    }

    if (result.status === 'APPROVED' && result.accessToken && result.refreshToken) {
      await saveTokens(result.accessToken, result.refreshToken);
      // 승인 창은 성공 문구("승인되었습니다…")를 잠깐 보여주고 닫는다.
      await closeLinkWindow(1_200);
      return;
    }
  }
}

/** 우리가 연 승인 창만 닫는다 — 사용자가 직접 열어 둔 우주인 탭은 건드리지 않는다. */
export async function closeLinkWindow(delayMs = 0): Promise<void> {
  const stored = await chrome.storage.local.get(LINK_WINDOW_KEY);
  const windowId = stored[LINK_WINDOW_KEY] as number | undefined;
  if (windowId === undefined) return;
  await chrome.storage.local.remove(LINK_WINDOW_KEY);
  if (delayMs > 0) await new Promise((resolve) => setTimeout(resolve, delayMs));
  try {
    await chrome.windows.remove(windowId);
  } catch {
    // 사용자가 이미 닫은 경우 — 무해하다
  }
}
