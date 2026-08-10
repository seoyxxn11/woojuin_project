import { clearTokens, getAccessToken, getRefreshToken, saveTokens } from '@/storage/authStorage';

const DEFAULT_API_BASE_URLS: Record<string, string> = {
  development: 'http://localhost:8080/api',
  demo: 'https://api.dev.woojuin.store/api',
  production: 'https://api.woojuin.store/api',
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
  ?? DEFAULT_API_BASE_URLS[import.meta.env.MODE]
  ?? DEFAULT_API_BASE_URLS.production;

// 웹앱 origin. 확장은 자체 로그인 폼이 없어 링크 코드 승인 창을 웹앱 로그인 화면으로 열고
// (deviceLink.ts), 팝업의 '우주인 열기'도 여기로 간다. 화면만 빌려 쓸 뿐 **세션은 웹과
// 완전히 별개다**(-498). API 주소와 짝을 맞춰 모드별로 둔다.
const DEFAULT_WEB_ORIGINS: Record<string, string> = {
  development: 'http://localhost:5173',
  demo: 'https://dev.woojuin.store',
  production: 'https://woojuin.store',
};

export const WEB_ORIGIN = import.meta.env.VITE_WEB_ORIGIN
  ?? DEFAULT_WEB_ORIGINS[import.meta.env.MODE]
  ?? DEFAULT_WEB_ORIGINS.production;

interface ApiResponse<T> { status: number; message: string; data: T }
interface TokenData { accessToken: string; refreshToken: string }

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
  }
}

let refreshPromise: Promise<string> | null = null;

async function parseResponse<T>(response: Response): Promise<ApiResponse<T>> {
  let body: ApiResponse<T> | null = null;
  try { body = (await response.json()) as ApiResponse<T>; } catch { /* non-JSON error */ }
  if (!response.ok || !body) {
    throw new ApiError(body?.message || `요청에 실패했습니다. (${response.status})`, response.status);
  }
  return body;
}

/**
 * refresh 거부로 볼 상태 코드 — 웹앱 client.ts 의 REFRESH_REJECTED_STATUSES 와 같은 계약이다.
 * 백엔드는 무효·만료·불일치·탈퇴를 전부 400 으로 준다(TokenRefreshService, S15P11C105-455).
 * 401 만 보면 **세션이 밖에서 끊긴 익스텐션**이 로그인 화면으로 못 가고 갇힌다 — 마이페이지
 * 기기 목록에서 "크롬 익스텐션"을 끊거나 탈퇴하면 refresh 가 400 으로 거부되는데, 팝업은
 * 401 에만 setAuthenticated(false) 를 하므로 로그인된 화면에서 서버 오류 문구만 반복해서
 * 보게 된다.
 */
const REFRESH_REJECTED_STATUSES = [400, 401, 403];

async function refreshAccessToken(): Promise<string> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    const refreshToken = await getRefreshToken();
    if (!refreshToken) throw new ApiError('로그인이 필요합니다.', 401);
    let data: TokenData;
    try {
      const response = await fetch(`${API_BASE_URL}/auth/token/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refreshToken }),
      });
      ({ data } = await parseResponse<TokenData>(response));
    } catch (error) {
      // 서버가 거부했을 때만 토큰을 지운다. 통신 실패(fetch 예외 등)로도 지워 버리면
      // 와이파이가 잠깐 끊긴 것만으로 로그아웃되는데, 웹앱은 이 경우 토큰을 남겨
      // 통신이 돌아오면 재시도한다 — 같은 정책을 따른다.
      if (error instanceof ApiError && REFRESH_REJECTED_STATUSES.includes(error.status)) {
        await clearTokens();
        // 팝업의 로그아웃 판정(error.status === 401)이 세 곳이라, 원래 상태 코드 대신
        // 401 로 통일해 던진다 — 400 을 그대로 흘리면 위 주석의 "갇히는" 증상이 된다.
        throw new ApiError('로그인이 만료되었습니다. 다시 로그인해 주세요.', 401);
      }
      throw error;
    }
    await saveTokens(data.accessToken, data.refreshToken);
    return data.accessToken;
  })().finally(() => { refreshPromise = null; });
  return refreshPromise;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  const accessToken = await getAccessToken();
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (response.status === 401 && retry) {
    const token = await refreshAccessToken();
    headers.set('Authorization', `Bearer ${token}`);
    return apiFetch<T>(path, { ...init, headers }, false);
  }
  return (await parseResponse<T>(response)).data;
}

export async function publicApiFetch<T>(path: string, init: RequestInit): Promise<T> {
  return (await parseResponse<T>(await fetch(`${API_BASE_URL}${path}`, init))).data;
}
