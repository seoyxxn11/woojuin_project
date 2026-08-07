import { Navigate, Outlet } from 'react-router-dom';
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

  if (accessToken) return <Navigate to="/home" replace />;

  return <Outlet />;
};

export default GuestOnly;
