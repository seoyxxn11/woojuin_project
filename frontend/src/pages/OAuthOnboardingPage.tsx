import { useEffect, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useAtom } from 'jotai';
import { updateMyProfile } from '@/services/auth';
import { useUser } from '@/hooks/useUser';
import { postLoginRedirectAtom } from '@/stores/authAtoms';
import BrandMark from '@/components/ui/BrandMark';
import TextInput from '@/components/ui/TextInput';
import SubmitButton from '@/components/ui/button/SubmitButton';
import PrivacyPolicyConsentCheckbox from '@/components/domain/auth/PrivacyPolicyConsentCheckbox';
import { nicknameSchema } from '@/schemas/authSchemas';

/**
 * 구글 로그인 온보딩 — 이메일 회원가입 폼과 같은 관문(닉네임 설정·개인정보처리방침 동의)을
 * 여기서 거치게 한다. 구글은 첫 로그인이 곧 가입이라 이 화면이 없으면 그 관문을 건너뛴다
 * (OAuthCallbackPage가 신규 가입일 때만 여기로 보낸다).
 *
 * 뒤로가기 버튼을 두지 않는다 — 이미 계정과 토큰이 만들어진 뒤라 "뒤로" 갈 의미 있는
 * 화면이 없고, 여기서 벗어나면 닉네임·동의 없이 앱에 들어가는 셈이 된다.
 */
const OAuthOnboardingPage = () => {
  const navigate = useNavigate();
  const { nickName, profileImageUrl, avatarColor, isLoading: isProfileLoading } = useUser();
  const [postLoginRedirect, setPostLoginRedirect] = useAtom(postLoginRedirectAtom);

  const [nickname, setNickname] = useState('');
  const [nicknamePrefilled, setNicknamePrefilled] = useState(false);
  const [agreedToPrivacyPolicy, setAgreedToPrivacyPolicy] = useState(false);

  // 구글이 준 기본 닉네임(OAuthAccountService가 이미 만들어 저장해 둔 값)으로 한 번만 채운다.
  // 그 다음부터는 사용자가 지운 빈 값을 다시 채워 넣지 않는다.
  useEffect(() => {
    if (!nicknamePrefilled && !isProfileLoading && nickName) {
      setNickname(nickName);
      setNicknamePrefilled(true);
    }
  }, [isProfileLoading, nickName, nicknamePrefilled]);

  const completeMutation = useMutation({
    mutationFn: () => updateMyProfile({ nickname: nickname.trim(), profileImageUrl, avatarColor }),
    onSuccess: () => {
      setPostLoginRedirect(null);
      navigate(postLoginRedirect ?? '/home', { replace: true });
    },
  });

  const nicknameResult = nicknameSchema.safeParse(nickname);
  const nicknameError =
    nickname.length > 0 && !nicknameResult.success ? nicknameResult.error.issues[0]?.message : null;
  const canSubmit = nicknameResult.success && agreedToPrivacyPolicy;

  return (
    <div className="min-h-dvh bg-space">
      <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center gap-6 px-6">
        <BrandMark className="justify-center" />

        <div className="flex w-full flex-col gap-4">
          <div>
            <h1 className="text-center text-lg font-bold text-text-1">거의 다 됐어요</h1>
            <p className="mt-1 text-center text-sm text-text-3">
              닉네임을 정하고 약관에 동의해 주세요
            </p>
          </div>

          <form
            className="flex flex-col gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (canSubmit) completeMutation.mutate();
            }}
          >
            <TextInput
              type="text"
              placeholder="닉네임"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              maxLength={20}
              aria-invalid={Boolean(nicknameError)}
              aria-describedby={nicknameError ? 'oauth-nickname-error' : undefined}
            />
            {nicknameError && (
              <p id="oauth-nickname-error" className="text-sm text-red-400">
                {nicknameError}
              </p>
            )}

            <PrivacyPolicyConsentCheckbox
              agreed={agreedToPrivacyPolicy}
              onAgree={() => setAgreedToPrivacyPolicy(true)}
            />

            <SubmitButton
              pending={completeMutation.isPending}
              pendingLabel="시작하는 중..."
              disabled={!canSubmit}
            >
              시작하기
            </SubmitButton>
          </form>
        </div>
      </main>
    </div>
  );
};

export default OAuthOnboardingPage;
