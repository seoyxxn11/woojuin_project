import LoginForm from '@/components/domain/auth/LoginForm';
import BrandMark from '@/components/ui/BrandMark';
import BackButton from '@/components/ui/BackButton';

/** 로그인 화면 — 폼은 모바일 랜딩과 공유한다 */
export default function LoginPage() {
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
