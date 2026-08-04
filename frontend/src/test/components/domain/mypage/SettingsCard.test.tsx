import { describe, expect, it, vi } from 'vitest';
import { render } from 'vitest-browser-react';
import { userEvent } from 'vitest/browser';
import { MemoryRouter } from 'react-router-dom';
import SettingsCard from '@/components/domain/mypage/SettingsCard';
import type { AiUsage } from '@/services/auth';

const limitedUsage: AiUsage = {
  period: '2026-07',
  used: 2,
  limit: 500,
  remaining: 498,
  unlimited: false,
  limitEnabled: true,
  resetAt: '2026-08-01T00:00:00+09:00',
};

// ChatIntegrationCard 가 ConnectedAppsCard 로 옮겨 가면서 이 카드엔 쿼리가 없다 —
// QueryClientProvider 없이 렌더된다.
const renderSettingsCard = (aiUsage: AiUsage) =>
  render(
    <MemoryRouter>
      <SettingsCard
        notificationEnabled
        onNotificationToggle={vi.fn()}
        aiUsage={aiUsage}
        aiUsageLoading={false}
        aiUsageError={false}
      />
    </MemoryRouter>,
  );

describe('마이페이지 설정 카드', () => {
  it('이번 달 AI 사용량과 AI 생성 안내를 표시한다', async () => {
    const { container } = await renderSettingsCard(limitedUsage);

    expect(container.textContent).toContain('이번 달 AI 사용량');
    expect(container.textContent).toContain(
      '아이템 1개를 저장할 때마다 AI가 제목·요약·카테고리를 생성해요.',
    );
    expect(container.textContent).toContain('2회 저장');
    expect(container.textContent).toContain('500회 한도');
    // 같은 숫자를 두 번 적지 않는다 — 진행바가 보이면 우측 요약 값은 접는다
    expect(container.textContent).not.toContain('2 / 500회');

    const progress = container.querySelector('[role="progressbar"]');
    expect(progress?.getAttribute('aria-valuenow')).toBe('2');
    expect(progress?.getAttribute('aria-valuemax')).toBe('500');
  });

  it('무제한 사용자는 누적 횟수와 무제한 상태를 표시한다', async () => {
    const { container } = await renderSettingsCard({
      ...limitedUsage,
      used: 42,
      remaining: null,
      unlimited: true,
    });

    expect(container.textContent).toContain('42회');
    expect(container.textContent).toContain('무제한');
    expect(container.querySelector('[role="progressbar"]')).toBeNull();
  });

  it('문의 이메일과 개인정보 처리방침 링크를 제공한다', async () => {
    const { container } = await renderSettingsCard(limitedUsage);

    expect(container.textContent).not.toContain('이메일 또는 MM으로 연락해 주세요.');

    const helpButton = [...container.querySelectorAll('button')].find((button) =>
      button.textContent?.includes('도움말 및 고객센터'),
    ) as HTMLButtonElement;
    await userEvent.click(helpButton);

    const emailLink = container.querySelector(
      'a[href="mailto:woojuin105@gmail.com"]',
    ) as HTMLAnchorElement;
    const privacyLink = container.querySelector('a[href="/privacy"]') as HTMLAnchorElement;

    expect(container.textContent).toContain('이메일 또는 MM으로 연락해 주세요.');
    expect(emailLink.textContent).toContain('woojuin105@gmail.com');
    expect(privacyLink.textContent).toContain('개인정보 처리방침');
  });
});
