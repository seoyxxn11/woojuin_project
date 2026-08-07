import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAtomValue, useSetAtom } from 'jotai';
import { useNavigate, useSearchParams } from 'react-router-dom';
import ConnectedAppsCard from '@/components/domain/mypage/ConnectedAppsCard';
import ConnectedDevicesCard from '@/components/domain/mypage/ConnectedDevicesCard';
import ProfileCard from '@/components/domain/mypage/ProfileCard';
import SettingsCard from '@/components/domain/mypage/SettingsCard';
import ConfirmModal from '@/components/ui/ConfirmModal';
import Toast, { type ToastMessage } from '@/components/ui/Toast';
import {
  fetchMyAiUsage,
  fetchMyStats,
  logout,
  updateMyProfile,
  withdraw,
  type UpdateProfilePayload,
} from '@/services/auth';
import { deleteNotificationToken } from '@/services/notifications';
import { accessTokenAtom, refreshTokenAtom } from '@/stores/authAtoms';
import { fcmTokenAtom } from '@/stores/pushAtoms';
import { useUser } from '@/hooks/useUser';
import { useSpaces } from '@/hooks/useSpaces';
import { tutorialReplayAtom, type TutorialReplayType } from '@/stores/tutorialAtoms';

type ConfirmKind = 'logout' | 'withdraw' | null;

const MyPage = () => {
  const user = useUser();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  // 크롬 익스텐션이 발급받은 링크 코드를 들고 승인하러 오는 진입 — /my?linkCode=XXXXXX
  // (S15P11C105-498). 승인 모달이 코드가 채워진 채로 바로 열린다. 로그인 전이면 AuthLayout 이
  // 로그인으로 보냈다가 postLoginRedirect 로 쿼리째 돌려보내므로 여기서 따로 챙길 것이 없다.
  const [searchParams] = useSearchParams();
  const linkCode = searchParams.get('linkCode') ?? undefined;
  const setAccessToken = useSetAtom(accessTokenAtom);
  const setRefreshToken = useSetAtom(refreshTokenAtom);
  const fcmToken = useAtomValue(fcmTokenAtom);
  const setFcmToken = useSetAtom(fcmTokenAtom);
  const setTutorialReplay = useSetAtom(tutorialReplayAtom);
  const { personalSpaceId, teams, isLoading: spacesLoading } = useSpaces();
  const [notificationEnabled, setNotificationEnabled] = useState(true);
  const [confirmKind, setConfirmKind] = useState<ConfirmKind>(null);
  const [toast, setToast] = useState<ToastMessage | null>(null);

  const { data: stats } = useQuery({
    queryKey: ['user', 'me', 'stats'],
    queryFn: fetchMyStats,
  });
  const {
    data: aiUsage,
    isPending: isAiUsagePending,
    isError: isAiUsageError,
  } = useQuery({
    queryKey: ['user', 'me', 'ai-usage'],
    queryFn: fetchMyAiUsage,
  });

  const profileMutation = useMutation({
    mutationFn: (payload: UpdateProfilePayload) => updateMyProfile(payload),
    onSuccess: (profile) => {
      queryClient.setQueryData(['user', 'me'], profile);
      setToast({ message: '프로필이 변경되었습니다.', tone: 'success' });
    },
    onError: () => {
      setToast({ message: '프로필을 변경하지 못했습니다. 다시 시도해 주세요.', tone: 'error' });
    },
  });

  const withdrawMutation = useMutation({
    mutationFn: withdraw,
    onSuccess: () => {
      setConfirmKind(null);
      setAccessToken(null);
      setRefreshToken(null);
      setFcmToken(null);
      queryClient.clear();
      navigate('/');
    },
    onError: () => {
      setToast({
        message: '회원 탈퇴에 실패했습니다. 다시 시도해 주세요.',
        tone: 'error',
      });
    },
  });

  const handleProfileUpdate = (changes: Partial<UpdateProfilePayload>) => {
    profileMutation.mutate({
      nickname: changes.nickname ?? user.nickName,
      profileImageUrl: changes.profileImageUrl ?? user.profileImageUrl ?? null,
      avatarColor: changes.avatarColor ?? user.avatarColor,
    });
  };

  const handleLogout = async () => {
    try {
      await logout();
      if (fcmToken) await deleteNotificationToken(fcmToken);
    } catch {
      // 서버 로그아웃이 실패해도 현재 기기의 인증 정보는 제거한다.
    }
    setAccessToken(null);
    setRefreshToken(null);
    setFcmToken(null);
    queryClient.clear();
    navigate('/');
  };

  /**
   * 세션이 서버에서 이미 끝난 뒤의 정리(현재 기기 해제·모든 기기 로그아웃).
   * handleLogout 과 달리 로그아웃 API 를 부르지 않는다 — 세션은 이미 없고,
   * 폐기된 토큰으로는 어떤 호출도 통과하지 않는다. 로컬만 정리하고 나간다.
   */
  const handleSessionEnded = () => {
    setAccessToken(null);
    setRefreshToken(null);
    setFcmToken(null);
    queryClient.clear();
    navigate('/');
  };

  const handleNotificationToggle = () => {
    setNotificationEnabled((enabled) => !enabled);
    setToast({
      message: `알림을 ${notificationEnabled ? '껐습니다.' : '켰습니다.'}`,
      tone: 'success',
    });
  };

  const handleTutorialReplay = (type: TutorialReplayType, workspaceId: number) => {
    setTutorialReplay({ type, workspaceId, requestId: Date.now() });
    navigate(`/workspace/${workspaceId}/universe`);
  };

  return (
    <div className="h-full overflow-y-auto px-4 pb-28 pt-[calc(24px+var(--safe-top))] desktop:px-9 desktop:pb-20">
      <div className="mx-auto w-full max-w-[660px]">
        <h1 className="mb-[26px] text-base font-bold text-text-1">마이페이지</h1>

        <ProfileCard
          nickname={user.nickName}
          email={user.email}
          avatarColor={user.avatarColor}
          provider={user.provider}
          saving={profileMutation.isPending}
          onNicknameChange={(nickname) => handleProfileUpdate({ nickname })}
          onAvatarColorChange={(avatarColor) => handleProfileUpdate({ avatarColor })}
          onLogout={() => setConfirmKind('logout')}
        />

        {/* 상자 없이 숫자만 나란히 — 위계는 타이포 크기가 만든다 */}
        <section aria-label="활동 통계" className="mb-10 flex gap-10 px-2">
          {[
            [stats?.totalSaved, '전체 저장'],
            [stats?.workspaceCount, '워크스페이스'],
            [stats?.savedThisWeek, '이번 주 저장'],
          ].map(([value, label]) => (
            <div key={String(label)} className="min-w-0">
              <div className="text-2xl font-extrabold tabular-nums text-text-1">
                {typeof value === 'number' ? value.toLocaleString('ko-KR') : '—'}
              </div>
              <div className="mt-1 text-xs text-text-3">{label}</div>
            </div>
          ))}
        </section>

        {/* 계정에 붙어 있는 것들(기기·앱)이 먼저, 사용량·도움말류 설정은 그 아래 */}
        <ConnectedDevicesCard
          onSessionEnded={handleSessionEnded}
          onError={(message) => setToast({ message, tone: 'error' })}
          initialLinkCode={linkCode}
        />
        <ConnectedAppsCard onError={(message) => setToast({ message, tone: 'error' })} />

        <SettingsCard
          notificationEnabled={notificationEnabled}
          onNotificationToggle={handleNotificationToggle}
          aiUsage={aiUsage}
          aiUsageLoading={isAiUsagePending}
          aiUsageError={isAiUsageError}
          personalSpaceId={personalSpaceId}
          sharedWorkspaceId={teams[0]?.id}
          spacesLoading={spacesLoading}
          onTutorialReplay={handleTutorialReplay}
        />

        <div className="mt-[34px] text-center">
          <button
            type="button"
            onClick={() => setConfirmKind('withdraw')}
            className="text-[11.5px] text-text-3 underline underline-offset-4 opacity-70 transition-opacity hover:opacity-100"
          >
            회원 탈퇴
          </button>
        </div>
      </div>

      <ConfirmModal
        open={confirmKind === 'logout'}
        title="로그아웃할까요?"
        description="현재 기기에서 우주인 계정을 로그아웃합니다."
        confirmLabel="로그아웃"
        onCancel={() => setConfirmKind(null)}
        onConfirm={handleLogout}
      />
      <ConfirmModal
        open={confirmKind === 'withdraw'}
        title="회원 탈퇴"
        description="정말 회원 탈퇴하시겠어요? 탈퇴하면 계정 이용이 중단되며, 저장된 데이터는 개인정보 처리방침에 따라 처리됩니다."
        confirmLabel={withdrawMutation.isPending ? '처리 중...' : '확인'}
        onCancel={() => setConfirmKind(null)}
        onConfirm={() => withdrawMutation.mutate()}
      />
      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </div>
  );
};

export default MyPage;
