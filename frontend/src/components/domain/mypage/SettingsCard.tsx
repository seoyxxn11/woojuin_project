import { useState } from 'react';
import { Link } from 'react-router-dom';
import Modal from '@/components/ui/Modal';
import type { AiUsage } from '@/services/auth';
import TutorialReplayCard from '@/components/domain/mypage/TutorialReplayCard';
import type { TutorialReplayType } from '@/stores/tutorialAtoms';

interface SettingsCardProps {
  // TODO: 알림 설정 기능을 다시 노출할 때 아래 두 prop과 주석 처리된 UI를 사용한다.
  notificationEnabled: boolean;
  onNotificationToggle: () => void;
  aiUsage?: AiUsage;
  aiUsageLoading: boolean;
  aiUsageError: boolean;
  personalSpaceId?: number;
  sharedWorkspaceId?: number;
  spacesLoading?: boolean;
  onTutorialReplay?: (type: TutorialReplayType, workspaceId: number) => void;
}

const SettingsCard = ({
  aiUsage,
  aiUsageLoading,
  aiUsageError,
  personalSpaceId,
  sharedWorkspaceId,
  spacesLoading = false,
  onTutorialReplay = () => undefined,
}: SettingsCardProps) => {
  const [helpOpen, setHelpOpen] = useState(false);
  const usagePercent =
    aiUsage && aiUsage.limitEnabled && !aiUsage.unlimited && aiUsage.limit > 0
      ? Math.min(100, (aiUsage.used / aiUsage.limit) * 100)
      : 0;
  const usageDescription = aiUsageError
    ? '사용량을 불러오지 못했습니다.'
    : aiUsageLoading
      ? '사용량을 불러오는 중입니다.'
      : '아이템 1개를 저장할 때마다 AI가 제목·요약·카테고리를 생성해요.';
  const showUsageBar = Boolean(aiUsage && aiUsage.limitEnabled && !aiUsage.unlimited);
  // 진행바가 보일 땐 우측 값을 접는다 — 바 아래 "N회 저장 / N회 한도"와 겹쳐 같은 숫자가 두 번 적힌다.
  // 바가 없는 상태(무제한·제한 없음·로딩·오류)에서는 이 값이 유일한 표시라 남긴다.
  const usageValue = aiUsageLoading
    ? '—'
    : aiUsageError
      ? '확인 불가'
      : aiUsage?.unlimited
        ? `${aiUsage.used.toLocaleString('ko-KR')}회`
        : '제한 없음';

  return (
    <>
      {/*
        TODO: 알림 설정 기능을 다시 사용할 때 BellIcon, RowIcon과 함께 주석을 해제한다.
        <section className="mb-4 rounded-[20px] border border-border-soft bg-surface p-1.5">
          <div className="flex items-center gap-3.5 rounded-md px-5 py-[13px] hover:bg-surface-2">
            <RowIcon>
              <BellIcon />
            </RowIcon>
            <div className="min-w-0 flex-1">
              <h2 className="text-sm font-semibold text-text-1">알림</h2>
              <p className="mt-0.5 text-xs text-text-3">AI 정리가 완료되면 알려드려요</p>
            </div>
            <button
              type="button"
              role="switch"
              aria-label="완료 알림"
              aria-checked={notificationEnabled}
              onClick={onNotificationToggle}
              className={[
                'relative h-6 w-[42px] shrink-0 rounded-pill transition-colors',
                notificationEnabled ? 'bg-accent' : 'bg-surface-3',
              ].join(' ')}
            >
              <span
                className={[
                  'absolute top-[3px] h-[18px] w-[18px] rounded-full transition-[left,background-color]',
                  notificationEnabled ? 'left-[21px] bg-white' : 'left-[3px] bg-text-2',
                ].join(' ')}
              />
            </button>
          </div>
        </section>
      */}
      {/* 사용량 블록과 행 두 개를 채움 하나에 — 테두리 없이 면의 톤 차로 구획한다 */}
      <section className="mb-8 overflow-hidden rounded-[20px] bg-surface">
        <div aria-labelledby="monthly-ai-usage-title" className="px-4 py-4">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <h2
                id="monthly-ai-usage-title"
                className="text-xs font-bold tracking-[0.1em] text-text-3"
              >
                이번 달 AI 사용량
              </h2>
              <p className="mt-2 text-xs text-text-3">{usageDescription}</p>
            </div>
            {!showUsageBar && (
              <span className="shrink-0 text-[18px] font-extrabold tabular-nums text-text-1">
                {usageValue}
              </span>
            )}
          </div>

          {aiUsage?.limitEnabled && !aiUsage.unlimited && (
            <div className="mt-4">
              <div
                role="progressbar"
                aria-label="이번 달 AI 사용량"
                aria-valuemin={0}
                aria-valuemax={aiUsage.limit}
                aria-valuenow={Math.min(aiUsage.used, aiUsage.limit)}
                className="h-2 overflow-hidden rounded-pill bg-surface-3"
              >
                <div
                  className="h-full rounded-pill bg-accent transition-[width]"
                  style={{ width: `${usagePercent}%` }}
                />
              </div>
              <div className="mt-1.5 flex justify-between text-[11px] text-text-3">
                <span>{aiUsage.used.toLocaleString('ko-KR')}회 저장</span>
                <span>{aiUsage.limit.toLocaleString('ko-KR')}회 한도</span>
              </div>
            </div>
          )}

          {aiUsage?.unlimited && (
            <span className="mt-3 inline-flex rounded-pill bg-surface-3 px-2.5 py-1 text-[11px] font-bold text-text-2">
              무제한
            </span>
          )}
        </div>

        {/* 채팅 앱 연동은 "연결된 앱" 섹션으로 옮겼다 — 연동 목록·해제와 한곳 */}
        <div className="border-t border-border-soft">
          <TutorialReplayCard
            personalSpaceId={personalSpaceId}
            sharedWorkspaceId={sharedWorkspaceId}
            loading={spacesLoading}
            onReplay={onTutorialReplay}
          />
        </div>
        <div className="border-t border-border-soft">
          <button
            type="button"
            onClick={() => setHelpOpen(true)}
            className="flex w-full items-center px-4 py-3.5 text-left hover:bg-surface-2"
          >
            <span className="flex-1 text-sm font-semibold text-text-1">도움말 및 고객센터</span>
            <span aria-hidden="true" className="text-lg leading-none text-text-3">
              ›
            </span>
          </button>
        </div>
      </section>

      <Modal open={helpOpen} onClose={() => setHelpOpen(false)} title="도움말 및 고객센터">
        <p className="text-[13px] leading-relaxed text-text-2">
          서비스 이용 중 오류나 문의 사항은 이메일 또는 MM으로 연락해 주세요.
        </p>

        <div className="mt-4 rounded-[14px] bg-surface-2 px-4 py-3.5">
          <p className="text-[11px] font-bold tracking-[0.08em] text-text-3">이메일</p>
          <a
            href="mailto:woojuin105@gmail.com"
            className="mt-1.5 inline-flex break-all text-[13px] font-semibold text-accent hover:text-accent-hover hover:underline"
          >
            woojuin105@gmail.com
          </a>
          <p className="mt-3 text-xs text-text-3">또는 팀 MM에서 편하게 문의해 주세요.</p>
        </div>

        <div className="mt-4 border-t border-border-soft pt-3">
          <Link
            to="/privacy"
            className="inline-flex text-xs font-medium text-text-2 hover:text-text-1 hover:underline"
          >
            개인정보 처리방침
          </Link>
        </div>
      </Modal>
    </>
  );
};

export default SettingsCard;
