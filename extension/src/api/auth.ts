import { apiFetch } from '@/api/client';
import { clearTokens } from '@/storage/authStorage';

/**
 * 로그인은 링크 코드(auth/deviceLink.ts)로 **확장 전용 세션**을 만든다 — 그래서 여기에
 * /auth/login 을 호출하는 함수가 없다. 확장이 자격 증명을 직접 받으면 웹앱의 로그인 수단을
 * 그대로 따라가지 못하고(구글 OAuth 는 확장 안에서 그대로 쓸 수도 없다), 확장이 비밀번호를
 * 만지게 되는 것도 피하고 싶다.
 *
 * 로그아웃은 서버에서 **이 세션만** 끊는다. 세션이 기기 단위라(-498) 웹이나 워치에는 아무
 * 영향이 없다 — 마이페이지 기기 목록에서 "크롬 익스텐션"이 사라지는 것이 전부다.
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
