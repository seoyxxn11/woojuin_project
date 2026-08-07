const ACCESS_TOKEN_KEY = 'accessToken';
const REFRESH_TOKEN_KEY = 'refreshToken';

/**
 * 저장 위치가 갈린다 — 팝업이 storage.onChanged 로 로그인 도착을 감지할 때 영역별로 키를
 * 봐야 하므로 밖에 알린다. (액세스 토큰은 브라우저를 닫으면 사라지는 session,
 * 리프레시 토큰은 다시 열어도 이어지도록 local)
 */
export const AUTH_STORAGE = {
  access: { area: 'session', key: ACCESS_TOKEN_KEY },
  refresh: { area: 'local', key: REFRESH_TOKEN_KEY },
} as const;

export async function getAccessToken(): Promise<string | null> {
  const result = await chrome.storage.session.get(ACCESS_TOKEN_KEY);
  return typeof result[ACCESS_TOKEN_KEY] === 'string' ? result[ACCESS_TOKEN_KEY] : null;
}

export async function getRefreshToken(): Promise<string | null> {
  const result = await chrome.storage.local.get(REFRESH_TOKEN_KEY);
  return typeof result[REFRESH_TOKEN_KEY] === 'string' ? result[REFRESH_TOKEN_KEY] : null;
}

export async function saveTokens(accessToken: string, refreshToken: string): Promise<void> {
  await Promise.all([
    chrome.storage.session.set({ [ACCESS_TOKEN_KEY]: accessToken }),
    chrome.storage.local.set({ [REFRESH_TOKEN_KEY]: refreshToken }),
  ]);
}

export async function clearTokens(): Promise<void> {
  await Promise.all([
    chrome.storage.session.remove(ACCESS_TOKEN_KEY),
    chrome.storage.local.remove(REFRESH_TOKEN_KEY),
  ]);
}
