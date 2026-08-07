import { apiFetch } from '@/api/client';
import { clearTokens } from '@/storage/authStorage';

/**
 * 로그인은 웹앱 로그인 화면을 쓰고 그 세션을 물려받는다 — 이유는 auth/webSession.ts 참고.
 * 그래서 여기에 /auth/login 을 호출하는 함수가 없다. 확장이 자격 증명을 직접 받으면 웹앱의
 * 로그인 수단을 그대로 따라가지 못하고(구글 OAuth 는 확장 안에서 그대로 쓸 수도 없다),
 * 확장이 비밀번호를 만지게 되는 것도 피하고 싶다.
 *
 * 로그아웃은 **서버 세션까지 끊는다.** 물려받기의 대가로 확장과 웹이 세션 하나를 나눠
 * 쓰므로, 열려 있는 우주인 탭도 다음 요청부터 로그아웃된다 — 의도된 결정이다. 토큰만
 * 지우던 처음 방식은 로그인 버튼이 살아 있는 웹 세션을 곧바로 다시 물려받아 "로그아웃이
 * 안 되는" 것처럼 보였다.
 */
export async function logout(): Promise<void> {
  try {
    await apiFetch<null>('/auth/logout', { method: 'POST' });
  } catch {
    // 세션이 이미 만료됐거나 통신이 없어도 로컬 로그아웃은 완주한다 — 서버에 남은
    // 세션은 refresh 만료로 소멸하고, 사용자 입장의 로그아웃을 막을 이유가 없다.
  }
  await clearTokens();
}
