import { describe, it, expect } from 'vitest';
import { render } from 'vitest-browser-react';
import ProgressBar from '@/components/ui/ProgressBar';

/** 진행 막대의 채움 비율을 실제 렌더 폭으로 계산 (browser mode 라 레이아웃이 실제로 계산된다) */
const fillRatio = (container: HTMLElement) => {
  const track = container.querySelector('[role="progressbar"]') as HTMLElement;
  const fill = track.firstElementChild as HTMLElement;
  return fill.getBoundingClientRect().width / track.getBoundingClientRect().width;
};

describe('ProgressBar', () => {
  it('라벨과 값을 단위와 함께 보여준다', async () => {
    const screen = await render(<ProgressBar label="저장 공간" value={12} max={20} unit="GB" />);
    await expect.element(screen.getByText('저장 공간')).toBeVisible();
    await expect.element(screen.getByText('12 / 20 GB')).toBeVisible();
  });

  it('value/max 비율만큼 채운다', async () => {
    const { container } = await render(<ProgressBar value={12} max={20} />);
    expect(fillRatio(container)).toBeCloseTo(0.6, 2);
  });

  it('max 가 0 이어도 깨지지 않는다', async () => {
    // 서버 응답 전 0/0 이 들어오면 NaN 이 width 에 박혀 막대가 깨진다
    const { container } = await render(<ProgressBar value={0} max={0} />);
    expect(fillRatio(container)).toBe(0);
  });

  it('value 가 max 를 넘어도 100% 에서 멈춘다', async () => {
    const { container } = await render(<ProgressBar value={999} max={20} />);
    expect(fillRatio(container)).toBeCloseTo(1, 2);
  });

  it('label 이 없으면 상단 행 없이 막대만 그린다', async () => {
    const { container } = await render(<ProgressBar value={1} max={2} />);
    expect(container.querySelectorAll('span')).toHaveLength(0);
    expect(container.querySelector('[role="progressbar"]')).not.toBeNull();
  });
});
