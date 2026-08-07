import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useSetAtom } from 'jotai';
import LoginForm from '@/components/domain/auth/LoginForm';
import BrandMark from '@/components/ui/BrandMark';
import BackButton from '@/components/ui/button/BackButton';
import { postLoginRedirectAtom } from '@/stores/authAtoms';

/** 로그인 화면 — 폼은 모바일 랜딩과 공유한다 */
export default function LoginPage() {
  const [searchParams] = useSearchParams();
  const setPostLoginRedirect = useSetAtom(postLoginRedirectAtom);

  // 익스텐션의 연결 로그인(-498): 익스텐션이 /login?linkCode= 로 창을 연다. 로그인을 마치면
  // 어떤 수단이든(이메일은 LoginForm, 구글은 콜백·온보딩) postLoginRedirect 를 따라
  // /my?linkCode= 로 가고, 거기서 익스텐션 대조가 성립하면 코드가 자동 승인돼 창이 닫힌다.
  // 사용자에게 이 흐름은 "로그인했더니 연결되고 창이 닫혔다"로 보인다.
  useEffect(() => {
    const linkCode = searchParams.get('linkCode');
    if (linkCode) setPostLoginRedirect(`/my?linkCode=${encodeURIComponent(linkCode)}`);
  }, [searchParams, setPostLoginRedirect]);

  return (
    <div className="relative min-h-dvh bg-space">
      <BackButton className="absolute left-4 top-4" />

      <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center gap-6 px-6">
        <BrandMark className="justify-center" />
        <LoginForm />
      </main>
    </div>
  );
}
