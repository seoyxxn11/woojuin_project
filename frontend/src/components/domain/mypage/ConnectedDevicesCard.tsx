import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import ConfirmModal from '@/components/ui/ConfirmModal';
import WatchLinkModal from '@/components/domain/mypage/WatchLinkModal';
import {
  fetchSessions,
  revokeAllSessions,
  revokeSession,
  type DeviceSession,
} from '@/services/auth';
import { formatRelativeDate } from '@/utils/formatDate';

interface ConnectedDevicesCardProps {
  /**
   * 이 기기의 세션이 끝났을 때(현재 기기 해제·모든 기기 로그아웃) 호출된다.
   * 서버 세션은 이미 사라진 뒤라, 로컬 토큰 정리와 로그인 화면 이동만 하면 된다.
   */
  onSessionEnded: () => void;
  onError: (message: string) => void;
  /**
   * `?linkCode=` 로 들어온 승인 요청 — 크롬 익스텐션이 코드를 발급받아 이 주소로 창을
   * 연다(S15P11C105-498). 있으면 승인 모달을 코드가 채워진 채로 바로 연다.
   */
  initialLinkCode?: string;
}

type PendingRevoke = { kind: 'one'; session: DeviceSession } | { kind: 'all' } | null;

const ConnectedDevicesCard = ({
  onSessionEnded,
  onError,
  initialLinkCode,
}: ConnectedDevicesCardProps) => {
  const queryClient = useQueryClient();
  const [pending, setPending] = useState<PendingRevoke>(null);
  const [watchLinkOpen, setWatchLinkOpen] = useState(false);

  // 익스텐션에서 넘어온 코드가 있으면 사용자가 버튼을 찾을 필요 없이 모달부터 연다.
  useEffect(() => {
    if (initialLinkCode) setWatchLinkOpen(true);
  }, [initialLinkCode]);

  // 오래된 목록으로 엉뚱한 세션을 끊으면 안 되므로 캐시하지 않고 화면을 열 때마다 다시 받는다.
  const {
    data: sessions,
    isPending,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['auth', 'sessions'],
    queryFn: fetchSessions,
    staleTime: 0,
    gcTime: 0,
    refetchOnMount: 'always',
  });

  const revokeOneMutation = useMutation({
    mutationFn: (session: DeviceSession) => revokeSession(session.sessionId),
    onSuccess: (_data, session) => {
      setPending(null);
      if (session.current) {
        onSessionEnded();
        return;
      }
      void queryClient.invalidateQueries({ queryKey: ['auth', 'sessions'] });
    },
    onError: () => {
      setPending(null);
      onError('기기를 로그아웃하지 못했습니다. 다시 시도해 주세요.');
    },
  });

  const revokeAllMutation = useMutation({
    mutationFn: revokeAllSessions,
    onSuccess: () => {
      setPending(null);
      onSessionEnded();
    },
    onError: () => {
      setPending(null);
      onError('모든 기기 로그아웃에 실패했습니다. 다시 시도해 주세요.');
    },
  });

  const busy = revokeOneMutation.isPending || revokeAllMutation.isPending;

  return (
    // 라벨은 밖에, 내용은 채움(fill) 안에 — 테두리 없이 면의 톤 차로 구획한다(iOS inset grouped)
    <section aria-labelledby="connected-devices-title" className="mb-8">
      <h2
        id="connected-devices-title"
        className="px-2 text-xs font-bold tracking-[0.1em] text-text-3"
      >
        연결된 기기
      </h2>

      <div className="mt-2 overflow-hidden rounded-[20px] bg-surface">
        {isPending && (
          <p className="px-4 py-4 text-[13px] text-text-3">기기 목록을 불러오는 중입니다…</p>
        )}

        {/* 통신이 안 될 때 빈 목록으로 보여주면 사용자가 "기기가 없다"고 오판한다 — 오류임을 밝히고 재시도를 준다 */}
        {isError && (
          <div className="flex items-center justify-between gap-3 px-4 py-4">
            <p className="text-[13px] text-text-2">기기 목록을 불러오지 못했습니다.</p>
            <button
              type="button"
              onClick={() => refetch()}
              className="shrink-0 rounded-lg px-3 py-1.5 text-xs font-bold text-accent hover:bg-surface-2"
            >
              다시 시도
            </button>
          </div>
        )}

        {sessions && (
          <>
            <ul>
              {sessions.map((session) => (
                <li
                  key={session.sessionId}
                  className="flex items-center gap-3 border-b border-border-soft px-4 py-3.5 last:border-b-0"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-semibold text-text-1">
                        {session.deviceName}
                      </span>
                      {session.current && (
                        <span className="shrink-0 rounded-pill bg-accent/15 px-2 py-0.5 text-[11px] font-bold text-accent">
                          이 기기
                        </span>
                      )}
                    </div>
                    <div className="mt-0.5 text-xs text-text-3">
                      마지막 사용 {formatRelativeDate(session.lastUsedAt) || '—'}
                    </div>
                  </div>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => setPending({ kind: 'one', session })}
                    className="shrink-0 rounded-lg px-2.5 py-1.5 text-xs font-bold text-text-3 hover:bg-surface-2 hover:text-text-1 disabled:opacity-50"
                  >
                    로그아웃
                  </button>
                </li>
              ))}
            </ul>

            {/* 기기 링크 코드 승인 진입점 — 워치·익스텐션이 띄운 코드를 여기서 입력한다
                (S15P11C105-458, -498) */}
            <button
              type="button"
              onClick={() => setWatchLinkOpen(true)}
              className="flex w-full items-center border-t border-border-soft px-4 py-3.5 text-left hover:bg-surface-2"
            >
              <span className="flex-1 text-sm font-semibold text-text-1">기기 연결</span>
              <span aria-hidden="true" className="text-lg leading-none text-text-3">
                ›
              </span>
            </button>

            {/* 위험 동작은 그룹 맨 아래 행 — 색이 무게를 다 말한다(iOS 로그아웃 행 문법) */}
            <button
              type="button"
              disabled={busy}
              onClick={() => setPending({ kind: 'all' })}
              className="flex w-full items-center border-t border-border-soft px-4 py-3 text-[13px] font-bold text-[#C74E4B] hover:bg-[#B3423F]/10 disabled:opacity-50"
            >
              모든 기기에서 로그아웃
            </button>
          </>
        )}
      </div>

      <WatchLinkModal
        open={watchLinkOpen}
        initialCode={initialLinkCode}
        onClose={() => setWatchLinkOpen(false)}
        onApproved={() => {
          void queryClient.invalidateQueries({ queryKey: ['auth', 'sessions'] });
          // 워치는 몇 초 간격으로 폴링한다 — 토큰을 받아 세션이 생긴 뒤 한 번 더 받아온다
          window.setTimeout(() => {
            void queryClient.invalidateQueries({ queryKey: ['auth', 'sessions'] });
          }, 4000);
        }}
      />

      <ConfirmModal
        open={pending?.kind === 'one'}
        title={
          pending?.kind === 'one' && pending.session.current
            ? '로그아웃할까요?'
            : '이 기기를 로그아웃할까요?'
        }
        description={
          pending?.kind === 'one' && pending.session.current
            ? '지금 쓰고 있는 기기입니다. 로그아웃하면 로그인 화면으로 이동합니다.'
            : `${pending?.kind === 'one' ? pending.session.deviceName : ''} 기기가 바로 로그아웃됩니다.`
        }
        confirmLabel={revokeOneMutation.isPending ? '처리 중…' : '로그아웃'}
        onCancel={() => setPending(null)}
        onConfirm={() => {
          if (pending?.kind === 'one' && !revokeOneMutation.isPending) {
            revokeOneMutation.mutate(pending.session);
          }
        }}
      />
      <ConfirmModal
        open={pending?.kind === 'all'}
        title="모든 기기에서 로그아웃할까요?"
        description="모든 기기가 바로 로그아웃되며, 이 기기도 로그인 화면으로 이동합니다. 비밀번호가 유출된 것 같을 때 사용하세요."
        confirmLabel={revokeAllMutation.isPending ? '처리 중…' : '모두 로그아웃'}
        onCancel={() => setPending(null)}
        onConfirm={() => {
          if (!revokeAllMutation.isPending) revokeAllMutation.mutate();
        }}
      />
    </section>
  );
};

export default ConnectedDevicesCard;
