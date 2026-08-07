import { WEB_ORIGIN } from '@/api/client';
import { isAutoLoginSuppressed, saveTokens } from '@/storage/authStorage';

/**
 * 웹앱 로그인 세션 물려받기.
 *
 * 확장에 자체 로그인 폼을 두지 않는 이유:
 *  - 웹앱이 제공하는 로그인 수단을 확장에서 **전부 다시 구현해야 한다**(LoginForm.tsx 기준
 *    현재 구글 OAuth 와 이메일·비밀번호 두 가지). 수단이 늘거나 줄 때마다 양쪽을 맞춰야 한다.
 *  - OAuth 를 확장 안에서 직접 하려면(chrome.identity) 백엔드가 확장용 redirect_uri 를
 *    받아주고 구글 콘솔에도 등록해야 한다.
 *  - 세션을 물려받으면 위 변경이 전부 불필요하고, 웹앱이 어떤 수단을 더하든 그대로 따라간다.
 *
 * 토큰은 웹앱이 localStorage 에 둔다(jotai atomWithStorage → JSON 문자열).
 * 확장 페이지·서비스워커는 host_permissions 가 있으면 그 탭에 스크립트를 넣어 읽을 수 있다.
 */
const ACCESS_STORAGE_KEY = 'woojuin:accessToken';
const REFRESH_STORAGE_KEY = 'woojuin:refreshToken';

/** atomWithStorage 는 값을 JSON 으로 넣는다 — 원문이 `"eyJhbGc..."` 처럼 따옴표째 들어 있다. */
function parseStoredToken(raw: string | null | undefined): string | null {
  if (!raw) return null;
  try {
    const value: unknown = JSON.parse(raw);
    return typeof value === 'string' && value.length > 0 ? value : null;
  } catch {
    return null;
  }
}

/** 로그인 창의 windowId. 서비스워커는 언제든 죽을 수 있어 메모리 대신 storage 에 둔다. */
const LOGIN_WINDOW_KEY = 'loginWindowId';

/** 백엔드가 토큰을 실어 보내는 콜백 경로 (OAuthCallbackPage 가 받는 그 주소) */
export const OAUTH_CALLBACK_PREFIX = `${WEB_ORIGIN}/oauth/callback`;

/**
 * 웹앱 로그인 화면을 **작은 팝업 창**으로 연다. 가입도 그 화면에서 이어서 할 수 있다.
 *
 * 탭이 아니라 팝업 창인 이유: 로그인만 받고 사라지는 흐름이라 사용자의 탭 목록을 어지럽히지
 * 않는 편이 낫다. 크기는 모바일 뷰에 가깝게 잡아 웹앱의 좁은 화면 레이아웃이 뜨게 한다.
 * 구글 로그인은 iframe 을 거부하지만 이건 진짜 브라우저 창이라 정상 동작한다.
 *
 * @param reauth 참이면 `?reauth=1` 로 연다 — 웹의 GuestOnly 가드가 이 파라미터를 보고,
 *   localStorage 에 토큰이 남아 있어도 /home 으로 보내지 않고 **로그인 폼을 보여준다.**
 *   로그아웃 뒤에 쓴다: 확장 로그아웃이 서버 세션을 끊어도 웹 localStorage 에는 죽은
 *   토큰이 남는데, 그 토큰이 리다이렉트를 태우면 폼이 뜨기도 전에 백그라운드가 죽은
 *   토큰을 주워 창을 닫아 버린다 — "로그인이 소리 없이 되는" 증상의 원인이었다.
 *   살아 있는 다른 세션이 있어도 폼이 뜨므로 계정 전환 경로이기도 하다.
 */
export async function openWebLogin(reauth = false): Promise<void> {
  const window = await chrome.windows.create({
    url: reauth ? `${WEB_ORIGIN}/login?reauth=1` : `${WEB_ORIGIN}/login`,
    type: 'popup',
    width: 460,
    height: 760,
    focused: true,
  });
  if (window.id !== undefined) {
    await chrome.storage.local.set({ [LOGIN_WINDOW_KEY]: window.id });
  }
}

/** 우리가 연 로그인 창의 windowId — 백그라운드가 "이 창에서 온 토큰인가"를 가를 때 쓴다. */
export async function getLoginWindowId(): Promise<number | undefined> {
  const stored = await chrome.storage.local.get(LOGIN_WINDOW_KEY);
  return stored[LOGIN_WINDOW_KEY] as number | undefined;
}

/**
 * OAuth 콜백 URL 에서 토큰을 채 간다.
 *
 * 웹앱이 localStorage 에 쓰기를 기다리지 않고 URL 에서 바로 읽는 이유: 콜백 주소에 토큰이
 * 그대로 들어 있어(백엔드가 그렇게 리다이렉트한다) 더 빠르고, 스크립트 주입도 필요 없다.
 * localStorage 수확(harvestWebSession)은 이미 로그인된 탭에서 이어받을 때 쓴다.
 *
 * @returns 토큰을 얻었는지
 */
export async function captureTokensFromCallback(
  url: string,
  { force = false }: { force?: boolean } = {},
): Promise<boolean> {
  if (!url.startsWith(OAUTH_CALLBACK_PREFIX)) return false;
  // 확장에서 로그아웃한 뒤라면 웹에서 로그인해도 따라 붙지 않는다 — 로그아웃을 존중한다.
  // 단 우리가 연 재로그인 창에서 온 콜백(force)은 예외다: 사용자가 확장의 로그인 버튼을
  // 눌러 연 창에서 직접 로그인한 것이므로, 그게 바로 차단을 푸는 명시적 동의다.
  if (!force && (await isAutoLoginSuppressed())) return false;
  const params = new URL(url).searchParams;
  const accessToken = params.get('accessToken');
  const refreshToken = params.get('refreshToken');
  if (!accessToken || !refreshToken) return false;
  await saveTokens(accessToken, refreshToken);
  return true;
}

/**
 * 로그인용으로 띄운 팝업 창을 닫는다. 사용자가 직접 열어 둔 우주인 창은 건드리지 않는다
 * (우리가 만든 windowId 만 닫는다).
 *
 * @param delayMs 닫기 전 여유. 웹앱이 자기 세션(localStorage)을 저장하고 다음 화면으로
 *   넘어갈 시간을 준다 — 즉시 닫으면 확장만 로그인되고 브라우저의 우주인 탭은 로그아웃
 *   상태로 남는다.
 */
export async function closeLoginWindow(delayMs = 700): Promise<void> {
  const stored = await chrome.storage.local.get(LOGIN_WINDOW_KEY);
  const windowId = stored[LOGIN_WINDOW_KEY] as number | undefined;
  if (windowId === undefined) return;
  await chrome.storage.local.remove(LOGIN_WINDOW_KEY);
  await new Promise((resolve) => setTimeout(resolve, delayMs));
  try {
    await chrome.windows.remove(windowId);
  } catch {
    // 사용자가 이미 닫은 경우 — 무해하다
  }
}

/**
 * 열려 있는 우주인 탭에서 토큰을 가져와 확장 저장소에 넣는다.
 *
 * @param tabId 특정 탭만 볼 때(백그라운드의 탭 갱신 감지). 없으면 우주인 탭 전체를 훑는다.
 * @returns 세션을 얻었는지
 */
export async function harvestWebSession(
  tabId?: number,
  { force = false }: { force?: boolean } = {},
): Promise<boolean> {
  // 자동 수확이 곧 자동 로그인이므로 여기서 막는다 — 호출하는 쪽(팝업 마운트·백그라운드 탭 감지)
  // 어디서도 가드를 빼먹지 않게 함수 안에 둔다. force 는 재로그인 창 전용이다: 그 창에서
  // 사용자가 직접 로그인한 결과를 걷는 것이라 차단 플래그보다 우선한다(background 참고).
  if (!force && (await isAutoLoginSuppressed())) return false;
  const targets = tabId === undefined
    ? (await chrome.tabs.query({ url: `${WEB_ORIGIN}/*` }))
        .map((tab) => tab.id)
        .filter((id): id is number => id !== undefined)
    : [tabId];

  for (const target of targets) {
    try {
      const [injection] = await chrome.scripting.executeScript({
        target: { tabId: target },
        // 페이지 컨텍스트에서 실행된다 — 확장 코드의 상수를 참조할 수 없어 키를 그대로 적는다.
        func: () => ({
          access: localStorage.getItem('woojuin:accessToken'),
          refresh: localStorage.getItem('woojuin:refreshToken'),
        }),
      });
      const accessToken = parseStoredToken(injection?.result?.access);
      const refreshToken = parseStoredToken(injection?.result?.refresh);
      // 액세스 토큰은 1시간짜리라 리프레시가 없으면 곧 만료된다 — 둘 다 있을 때만 인정한다.
      if (accessToken && refreshToken) {
        await saveTokens(accessToken, refreshToken);
        return true;
      }
    } catch {
      // 탭이 닫혔거나(권한 회수 포함) 주입이 막힌 경우 — 다음 탭을 본다.
    }
  }
  return false;
}

/**
 * 열려 있는 우주인 탭들의 웹 세션을 지운다 — 확장 로그아웃의 마무리.
 *
 * 서버 세션은 이미 끊었지만(api/auth.ts) 웹 탭은 **다음 요청을 보내기 전까지 그걸 모른다** —
 * localStorage 의 죽은 토큰으로 로그인된 화면을 계속 그린다. 사용자에겐 "익스텐션에서
 * 로그아웃했는데 웹은 그대로"로 보인다.
 *
 * 토큰을 지우는 것만으로는 부족하다: 같은 탭 안에서의 localStorage 변경은 storage 이벤트가
 * 발생하지 않아 웹앱의 atomWithStorage 구독이 모른다. 그래서 이벤트를 손으로 쏜다 — 받으면
 * 토큰 atom 이 null 이 되고 AuthLayout 이 즉시 로그인 화면으로 보낸다(프리뷰로 확인:
 * /workspace/… 에서 곧바로 랜딩으로 이동). 주입이 막힌 탭은 다음 요청의 401이 정리한다.
 */
export async function clearWebSessions(): Promise<void> {
  const tabs = await chrome.tabs.query({ url: `${WEB_ORIGIN}/*` });
  await Promise.all(tabs.map(async (tab) => {
    if (tab.id === undefined) return;
    try {
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        // 페이지 컨텍스트 — 확장 상수를 못 쓰므로 키를 그대로 적는다(harvest 와 같은 이유).
        func: () => {
          for (const key of ['woojuin:accessToken', 'woojuin:refreshToken']) {
            localStorage.removeItem(key);
            window.dispatchEvent(
              new StorageEvent('storage', { key, newValue: null, storageArea: localStorage }),
            );
          }
        },
      });
    } catch {
      // 탭이 방금 닫혔거나 주입이 거부된 경우 — 무해하다(위 javadoc).
    }
  }));
}

export { ACCESS_STORAGE_KEY, REFRESH_STORAGE_KEY };
