import { useMutation } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAtom, useSetAtom } from 'jotai';
import axios from 'axios';
import { login } from '@/services/auth';
import { loginSchema, type LoginFormValues } from '@/schemas/authSchemas';
import { accessTokenAtom, postLoginRedirectAtom, refreshTokenAtom } from '@/stores/authAtoms';
import FormTextField from '@/components/ui/form/FormTextField';
import SubmitButton from '@/components/ui/button/SubmitButton';
import GoogleAuthButton from './GoogleAuthButton';

/**
 * 로그인 폼 — /login 페이지와 모바일 랜딩이 함께 쓴다.
 *
 * 페이지 레이아웃(가운데 정렬·배경)은 쓰는 쪽이 정하고 여기서는 폼만 그린다.
 * autoFocus 를 두지 않는 이유: 랜딩에서는 데스크톱용 마크업과 함께 DOM 에 있고
 * CSS 로만 감춰지므로, 자동 포커스가 엉뚱한 곳으로 튈 수 있다.
 */
const LoginForm = () => {
  const navigate = useNavigate();
  const formMethods = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });
  const setAccessToken = useSetAtom(accessTokenAtom);
  const setRefreshToken = useSetAtom(refreshTokenAtom);
  const [postLoginRedirect, setPostLoginRedirect] = useAtom(postLoginRedirectAtom);

  const loginMutation = useMutation({
    mutationFn: login,
    // 토큰 저장과 도착지 결정은 구글 로그인(OAuthCallbackPage)과 같은 규칙을 따른다 —
    // AuthLayout 이 로그인 전 경로를 postLoginRedirect 에 남겨두므로 그리로 돌려보낸다.
    onSuccess: ({ accessToken, refreshToken }) => {
      setAccessToken(accessToken);
      setRefreshToken(refreshToken);
      setPostLoginRedirect(null);
      navigate(postLoginRedirect ?? '/home', { replace: true });
    },
  });

  // 자격 증명이 틀렸는지(401) 서버가 죽었는지는 사용자가 할 수 있는 일이 다르므로
  // 서버 메시지를 그대로 보여주고, 메시지가 없을 때만 기본 문구로 떨어진다.
  const errorMessage = loginMutation.isError
    ? ((axios.isAxiosError(loginMutation.error)
        ? loginMutation.error.response?.data?.message
        : null) ?? '로그인에 실패했습니다')
    : null;

  return (
    <div className="flex w-full flex-col gap-4">
      <form
        className="flex flex-col gap-3"
        onSubmit={formMethods.handleSubmit((values) => loginMutation.mutate(values))}
      >
        <FormTextField type="email" placeholder="이메일" name="email" formMethods={formMethods} />
        <FormTextField
          type="password"
          placeholder="비밀번호"
          name="password"
          formMethods={formMethods}
        />
        {errorMessage && <p className="text-sm text-red-400">{errorMessage}</p>}
        <SubmitButton pending={loginMutation.isPending} pendingLabel="로그인 중...">
          로그인
        </SubmitButton>
      </form>

      {/* 구글 Cloud 프로젝트 정지 기간(2026-08-04~08-06) 동안 감춰 뒀던 버튼 — 계정이 복구돼 되살린다.
          이메일 로그인은 그대로 남긴다: 그 기간에 가입한 LOCAL 계정들이 유일한 진입로를 잃는다. */}
      <GoogleAuthButton />

      {/* 구글은 첫 로그인이 곧 가입이라(OAuthAccountService.findOrCreateUser) 여기에도 고지한다 */}
      <p className="text-center text-xs text-text-3">
        로그인하면{' '}
        <Link to="/privacy" className="underline underline-offset-2 hover:text-text-2">
          개인정보처리방침
        </Link>
        에 동의하는 것으로 봅니다.
      </p>

      <p className="text-center text-sm text-text-3">
        계정이 없으신가요?{' '}
        {/* replace — 로그인·가입은 서로 오가는 관문이라 히스토리에 쌓을 이유가 없고, 남으면
            로그인 뒤 뒤로가기가 GuestOnly 에 되돌려져 "눌러도 아무 일이 없는" 상태가 된다.
            돌아올 길은 반대쪽 화면의 같은 링크가 맡는다. */}
        <Link to="/signup" replace className="font-semibold text-accent hover:text-accent-hover">
          회원가입
        </Link>
      </p>
    </div>
  );
};

export default LoginForm;
