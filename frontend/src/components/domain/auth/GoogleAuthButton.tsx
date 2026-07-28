import { backendOrigin } from '@/services/client';

/** 구글 4색 "G" 마크 — 공식 자산이라 색·형태를 바꾸지 않는다 */
const GoogleMark = () => (
  <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true" className="shrink-0">
    <path
      fill="#EA4335"
      d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
    />
    <path
      fill="#4285F4"
      d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
    />
    <path
      fill="#FBBC05"
      d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
    />
    <path
      fill="#34A853"
      d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
    />
  </svg>
);

interface GoogleAuthButtonProps {
  /** 버튼 문구 — 구글 가이드가 허용하는 문구만 쓴다 */
  label?: string;
}

/**
 * 구글 계정으로 로그인.
 *
 * 4색 G 마크는 공식 자산이라 그대로 두고, 버튼 껍데기는 우리 폼 양식을 따른다
 * (입력칸과 같은 bg-surface-2 · border · rounded-md). 흰 버튼은 다크 테마에서 혼자 튄다.
 *
 * <a> 인 이유: OAuth 는 백엔드로 전체 페이지 이동이라 fetch 가 아니다.
 */
const GoogleAuthButton = ({ label = 'Google 계정으로 로그인' }: GoogleAuthButtonProps) => (
  <a
    href={`${backendOrigin}/oauth2/authorization/google`}
    className="flex h-10 items-center justify-center gap-3 rounded-md border border-border bg-surface-2 px-3 text-sm font-semibold text-text-1 transition-colors hover:border-accent hover:bg-surface-3"
  >
    <GoogleMark />
    {label}
  </a>
);

export default GoogleAuthButton;
