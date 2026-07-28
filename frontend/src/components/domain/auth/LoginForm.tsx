import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useSetAtom } from 'jotai';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { login } from '@/services/auth';
import { accessTokenAtom, refreshTokenAtom } from '@/stores/authAtoms';
import TextInput from '@/components/ui/TextInput';
import SubmitButton from '@/components/ui/SubmitButton';
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
  const setAccessToken = useSetAtom(accessTokenAtom);
  const setRefreshToken = useSetAtom(refreshTokenAtom);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: (tokens) => {
      setAccessToken(tokens.accessToken);
      setRefreshToken(tokens.refreshToken);
      navigate('/home');
    },
  });

  const errorMessage = axios.isAxiosError(loginMutation.error)
    ? (loginMutation.error.response?.data?.message ?? '로그인에 실패했습니다')
    : null;

  return (
    <div className="flex w-full flex-col gap-4">
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          loginMutation.mutate({ email, password });
        }}
      >
        <TextInput
          type="email"
          placeholder="이메일"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <TextInput
          type="password"
          placeholder="비밀번호"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {errorMessage && <p className="text-sm text-red-400">{errorMessage}</p>}
        <SubmitButton pending={loginMutation.isPending} pendingLabel="로그인 중...">
          로그인
        </SubmitButton>
      </form>

      <GoogleAuthButton />

      <p className="text-center text-sm text-text-3">
        계정이 없으신가요?{' '}
        <Link to="/signup" className="font-semibold text-accent hover:text-accent-hover">
          회원가입
        </Link>
      </p>
    </div>
  );
};

export default LoginForm;
