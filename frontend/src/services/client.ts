import axios from 'axios';
import { jotaiStore } from '@/stores/jotaiStore';
import { accessTokenAtom, refreshTokenAtom } from '@/stores/authAtoms';

/** 공통 API 응답 형식 (API 명세서 기준) */
export interface ApiResponse<T> {
  status: number;
  message: string;
  data: T;
}

interface TokenPair {
  accessToken: string;
  refreshToken: string;
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: 10_000,
});

// 구글 로그인(oauth2/authorization/...)은 /api 아래가 아니라 백엔드 루트 경로라서
// 별도로 origin만 떼어 써야 한다. VITE_API_BASE_URL이 비어있으면(설정 누락 등)
// baseURL이 '/api'(상대경로)로 떨어지는데, 그걸 그대로 잘라내면 빈 문자열이 되어
// 버튼이 프론트 자기 자신으로 이동해버리니 절대 URL 기본값을 둔다.
export const backendOrigin =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/api\/?$/, '') || 'http://localhost:8080';

// refresh 호출 전용. api 인스턴스로 호출하면 인터셉터가 다시 붙어
// 만료된 access token을 헤더에 실은 채 요청하게 되니 별도 인스턴스를 쓴다.
const refreshClient = axios.create({
  baseURL: api.defaults.baseURL,
  timeout: 10_000,
});

api.interceptors.request.use((config) => {
  const accessToken = jotaiStore.get(accessTokenAtom);
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = jotaiStore.get(refreshTokenAtom);
  if (!refreshToken) return null;

  try {
    const { data } = await refreshClient.post<ApiResponse<TokenPair>>('/auth/token/refresh', {
      refreshToken,
    });
    jotaiStore.set(accessTokenAtom, data.data.accessToken);
    jotaiStore.set(refreshTokenAtom, data.data.refreshToken);
    return data.data.accessToken;
  } catch {
    jotaiStore.set(accessTokenAtom, null);
    jotaiStore.set(refreshTokenAtom, null);
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      // 동시에 여러 요청이 401을 맞아도 refresh는 한 번만 나가도록 진행 중인 요청을 공유한다.
      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
      const newAccessToken = await refreshPromise;
      if (newAccessToken) {
        original.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(original);
      }
    }
    return Promise.reject(error);
  },
);
