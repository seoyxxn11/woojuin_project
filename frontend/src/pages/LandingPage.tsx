import { Link } from 'react-router-dom';
import LandingHeader from '@/components/domain/landing/LandingHeader';
import LoginForm from '@/components/domain/auth/LoginForm';
import BrandMark from '@/components/ui/BrandMark';

/**
 * 진입 화면 — sm(640px)을 기준으로 성격이 갈린다.
 *
 *   < sm  폰 세로. 소개를 읽을 자리가 없어 로그인/회원가입을 바로 띄운다
 *   >= sm 헤더 + 서비스 소개. 로그인은 우측 상단 버튼으로
 *
 * 분기는 CSS 로만 한다(JS 미디어쿼리 X). 둘 다 DOM 에 있고 한쪽만 보인다 —
 * 창 폭을 바꾸면 새로고침 없이 즉시 전환된다.
 */
const LandingPage = () => (
  <div className="min-h-dvh bg-space text-text-1">
    {/* ── 모바일: 로고 + 로그인 폼 ───────────────────────── */}
    <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center gap-8 px-6 desktop:hidden">
      <BrandMark size={40} className="justify-center" />
      <LoginForm />
    </main>

    {/* ── 데스크톱: 헤더 + 소개 ──────────────────────────── */}
    <div className="hidden desktop:block">
      <LandingHeader />

      {/* TODO: 목업 v3.5/landing.html 본문(히어로·기능·둘러보기) 이식 */}
      <main className="mx-auto flex min-h-dvh max-w-3xl flex-col items-center justify-center gap-6 px-8 text-center">
        <h1 className="text-hero font-extrabold tracking-[-0.02em]">저장은 1초, 정리는 AI가</h1>
        <p className="text-lg text-text-2">
          링크·사진·메모를 던져두면 우주인이 알아서 별자리로 정리합니다.
        </p>
        <Link
          to="/login"
          className="rounded-md bg-accent px-6 py-3 font-semibold text-white transition-colors hover:bg-accent-hover"
        >
          시작하기
        </Link>
      </main>
    </div>
  </div>
);

export default LandingPage;
