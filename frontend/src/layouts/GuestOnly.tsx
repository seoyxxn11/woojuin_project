import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAtomValue } from 'jotai';
import { accessTokenAtom } from '@/stores/authAtoms';

/**
 * 로그인 전 화면들(랜딩·로그인·가입)을 감싼다 — 이미 로그인돼 있으면 앱으로 보낸다.
 * AuthLayout 의 반대쪽 가드다.
 *
 * 이게 없으면 **설치형 PWA 를 껐다 켤 때마다 랜딩 페이지가 뜬다.** PWA 는 cold start 마다
 * manifest 의 start_url(`/`)로 진입하는데, `/` 는 AuthLayout 밖이고 LandingPage 는 인증을
 * 보지 않으므로 토큰이 멀쩡히 있어도 마케팅 화면이 그려진다. 사용자에게는 "로그인이 풀렸다"로
 * 보이지만 실제로는 앱으로 들어가는 길이 없는 것이다.
 *
 * 브라우저에서도 같다 — 로그인한 채 `/` 나 `/login` 을 열면 로그인 폼이 나온다.
 *
 * 두 가드가 서로를 밀어낼 일은 없다. 조건이 accessToken 유무로 정확히 반대라서 한쪽만
 * 성립한다. 첫 렌더부터 값이 맞는 것도 전제인데(authAtoms 의 `getOnInit: true`), 그게 없으면
 * 여기서 한 프레임 랜딩이 번쩍이고 AuthLayout 은 반대로 로그인 화면으로 튕겨낸다.
 */
const GuestOnly = () => {
  const accessToken = useAtomValue(accessTokenAtom);
  const location = useLocation();

  // ?reauth=1 이면 토큰이 있어도 폼을 보여준다 — 익스텐션의 재로그인 창이 쓴다.
  // 익스텐션에서 로그아웃하면 서버 세션이 끊기는데 localStorage 에는 죽은 토큰이 남고,
  // 그 죽은 토큰이 이 리다이렉트를 태우면 로그인 창이 폼을 보여주지도 못하고 /home 으로
  // 넘어가 버린다(익스텐션은 그 페이지에서 죽은 토큰을 주워 조용히 닫힌다). 명시적으로
  // "다시 로그인하겠다"는 진입이므로 세션이 살아 있어도 폼이 맞다 — 계정 전환 경로이기도 하다.
  const reauth = new URLSearchParams(location.search).has('reauth');

  if (accessToken && !reauth) return <Navigate to="/home" replace />;

  return <Outlet />;
};

export default GuestOnly;
