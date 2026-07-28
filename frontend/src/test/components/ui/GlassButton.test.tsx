import { describe, it, expect } from 'vitest';
import { render } from 'vitest-browser-react';
import GlassButton from '@/components/ui/GlassButton';
import { PlusIcon } from '@/assets/icons';

const btnOf = (c: HTMLElement) => c.querySelector('button')!;

describe('GlassButton', () => {
  it('기본은 type=button 이다', async () => {
    // 폼 안에 놓였을 때 실수로 제출되면 안 된다
    const { container } = await render(<GlassButton icon={<PlusIcon />} />);
    expect(btnOf(container)).toHaveAttribute('type', 'button');
  });

  describe('모양 — 목업 v3.5 noti/share 버튼', () => {
    it('라벨이 없으면 40×38 정사각이다', async () => {
      const { container } = await render(<GlassButton icon={<PlusIcon />} aria-label="추가" />);
      const rect = btnOf(container).getBoundingClientRect();
      expect(rect.width).toBeCloseTo(40, 1);
      expect(rect.height).toBeCloseTo(38, 1);
    });

    it('라벨이 있으면 알약형으로 넓어진다', async () => {
      const { container } = await render(<GlassButton icon={<PlusIcon />} label="공유" />);
      const rect = btnOf(container).getBoundingClientRect();
      expect(rect.width).toBeGreaterThan(40);
      // 높이는 아이콘만 있을 때와 같아야 헤더에서 줄이 맞는다
      expect(rect.height).toBeCloseTo(38, 1);
    });

    it('아이콘은 16px 이다', async () => {
      const { container } = await render(<GlassButton icon={<PlusIcon />} aria-label="추가" />);
      const rect = container.querySelector('svg')!.getBoundingClientRect();
      expect(rect.width).toBeCloseTo(16, 1);
    });
  });

  it('badge 를 아이콘 위에 겹쳐 얹는다', async () => {
    // 알림 안 읽음 점처럼 버튼 모서리에 붙는 표시
    const { container } = await render(
      <GlassButton icon={<PlusIcon />} aria-label="알림" badge={<span data-testid="dot" />} />,
    );
    expect(container.querySelector('[data-testid="dot"]')).not.toBeNull();
  });

  it('라벨이 없을 때 aria-label 로 이름을 준다', async () => {
    const { container } = await render(
      <GlassButton icon={<PlusIcon />} aria-label="새로 만들기" />,
    );
    expect(btnOf(container)).toHaveAttribute('aria-label', '새로 만들기');
  });
});
