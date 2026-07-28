import { atomWithStorage } from 'jotai/utils';

// localStorage를 직접 쓰지 않고 Jotai atomWithStorage로 감싼다 (AGENTS.md 컨벤션).
// getOnInit: true로 안 두면 첫 렌더에서 무조건 initialValue(null)부터 시작해서
// (마운트 이펙트가 돌기 전까지) 로그인돼 있어도 "토큰 없음"으로 보인다 —
// AuthLayout의 가드가 이 첫 렌더 타이밍에 반응해 즉시 리다이렉트시켜버렸었다.
export const accessTokenAtom = atomWithStorage<string | null>(
  'woojuin:accessToken',
  null,
  undefined,
  {
    getOnInit: true,
  },
);
export const refreshTokenAtom = atomWithStorage<string | null>(
  'woojuin:refreshToken',
  null,
  undefined,
  {
    getOnInit: true,
  },
);
