import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from 'vitest-browser-react';
import { userEvent, page } from 'vitest/browser';
import HeaderPopover from '@/components/ui/HeaderPopover';

const panelOf = (c: HTMLElement) => c.querySelector('[role="dialog"]');
const triggerOf = (c: HTMLElement) => c.querySelector('button')!;

const setup = (children: React.ReactNode = <p>내용</p>, onClick?: () => void) =>
  render(
    <HeaderPopover trigger={<button onClick={onClick}>열기</button>}>{children}</HeaderPopover>,
  );

describe('HeaderPopover', () => {
  describe('여닫기', () => {
    it('처음에는 닫혀 있다', async () => {
      const { container } = await setup();
      expect(panelOf(container)).toBeNull();
    });

    it('트리거를 누르면 열린다', async () => {
      const { container } = await setup();
      await userEvent.click(triggerOf(container));
      expect(panelOf(container)).not.toBeNull();
    });

    it('트리거를 다시 누르면 닫힌다 (토글)', async () => {
      const { container } = await setup();
      const trigger = triggerOf(container);
      await userEvent.click(trigger);
      await userEvent.click(trigger);
      expect(panelOf(container)).toBeNull();
    });

    it('ESC 로 닫힌다', async () => {
      const { container } = await setup();
      await userEvent.click(triggerOf(container));
      await userEvent.keyboard('{Escape}');
      expect(panelOf(container)).toBeNull();
    });

    it('바깥을 누르면 닫힌다', async () => {
      const { container } = await setup();
      await userEvent.click(triggerOf(container));
      await userEvent.click(document.body);
      expect(panelOf(container)).toBeNull();
    });

    it('패널 안을 눌러도 닫히지 않는다', async () => {
      // 폼을 채우는 도중에 닫히면 입력이 날아간다
      const { container } = await setup(<p>내용</p>);
      await userEvent.click(triggerOf(container));
      await userEvent.click(panelOf(container)!);
      expect(panelOf(container)).not.toBeNull();
    });
  });

  describe('트리거 위임', () => {
    it('트리거가 원래 갖고 있던 onClick 도 함께 호출한다', async () => {
      // 토글을 주입하느라 소비처의 onClick 을 덮어쓰면 안 된다
      const onClick = vi.fn();
      const { container } = await setup(<p>내용</p>, onClick);
      await userEvent.click(triggerOf(container));
      expect(onClick).toHaveBeenCalledOnce();
    });
  });

  describe('children 이 함수면 close 를 받는다', () => {
    it('내부에서 close 를 부르면 닫힌다', async () => {
      // 저장 성공 후 폼이 스스로 팝오버를 닫을 수 있어야 한다
      const { container } = await render(
        <HeaderPopover trigger={<button>열기</button>}>
          {(close) => <button onClick={close}>닫기</button>}
        </HeaderPopover>,
      );
      await userEvent.click(triggerOf(container));
      const closeBtn = [...container.querySelectorAll('button')].find(
        (b) => b.textContent === '닫기',
      )!;
      await userEvent.click(closeBtn);
      expect(panelOf(container)).toBeNull();
    });
  });

  describe('접근성', () => {
    it('열림 상태를 aria-expanded 로 알린다', async () => {
      const { container } = await setup();
      const trigger = triggerOf(container);
      expect(trigger).toHaveAttribute('aria-expanded', 'false');
      await userEvent.click(trigger);
      expect(trigger).toHaveAttribute('aria-expanded', 'true');
    });

    it('aria-controls 가 실제 패널 id 를 가리킨다', async () => {
      const { container } = await setup();
      const trigger = triggerOf(container);
      await userEvent.click(trigger);
      expect(trigger.getAttribute('aria-controls')).toBe(panelOf(container)!.id);
    });

    it('팝오버를 여는 버튼임을 aria-haspopup 으로 알린다', async () => {
      const { container } = await setup();
      expect(triggerOf(container)).toHaveAttribute('aria-haspopup', 'true');
    });
  });

  describe('위치 — 데스크톱(>= lg): 목업 v3.5 (top: 100% + 8px, right: 0)', () => {
    it('트리거 바로 아래 8px 간격으로 뜬다', async () => {
      const { container } = await setup();
      const trigger = triggerOf(container);
      await userEvent.click(trigger);

      const t = trigger.getBoundingClientRect();
      const p = panelOf(container)!.getBoundingClientRect();
      expect(p.top - t.bottom).toBeGreaterThan(6);
      expect(p.top - t.bottom).toBeLessThan(10);
    });

    it('트리거 오른쪽 끝에 맞춰 정렬된다', async () => {
      // 헤더 우측에 붙는 버튼이라 왼쪽으로 펼쳐져야 화면 밖으로 안 나간다
      const { container } = await setup();
      const trigger = triggerOf(container);
      await userEvent.click(trigger);

      const t = trigger.getBoundingClientRect();
      const p = panelOf(container)!.getBoundingClientRect();
      expect(Math.abs(t.right - p.right)).toBeLessThan(2);
    });
  });

  describe('위치 — 모바일(< lg): 화면 한가운데', () => {
    // 좁은 화면에서 트리거에 붙여 두면 패널이 화면 밖으로 밀린다
    beforeEach(async () => {
      await page.viewport(375, 812);
    });
    afterEach(async () => {
      await page.viewport(1280, 800);
    });

    it('트리거가 아니라 화면 중앙에 뜬다', async () => {
      const { container } = await setup();
      await userEvent.click(triggerOf(container));

      const p = panelOf(container)!.getBoundingClientRect();
      expect(p.left + p.width / 2).toBeCloseTo(window.innerWidth / 2, 0);
      expect(p.top + p.height / 2).toBeCloseTo(window.innerHeight / 2, 0);
    });

    it('화면 밖으로 넘치지 않는다', async () => {
      const { container } = await setup();
      await userEvent.click(triggerOf(container));

      const p = panelOf(container)!.getBoundingClientRect();
      expect(p.left).toBeGreaterThanOrEqual(0);
      expect(p.right).toBeLessThanOrEqual(window.innerWidth);
    });

    it('뒤를 덮는 배경이 생기고, 누르면 닫힌다', async () => {
      const { container } = await setup();
      await userEvent.click(triggerOf(container));

      const backdrop = container.querySelector('.fixed.inset-0') as HTMLElement;
      expect(backdrop).not.toBeNull();

      // 패널을 피해 화면 위쪽 끝을 눌러야 배경이 잡힌다
      await userEvent.click(backdrop, { position: { x: 10, y: 10 } });
      expect(panelOf(container)).toBeNull();
    });
  });

  describe('배경 — 데스크톱에서는 없다', () => {
    it('앵커된 팝오버라 화면을 덮지 않는다', async () => {
      const { container } = await setup();
      await userEvent.click(triggerOf(container));

      const backdrop = container.querySelector('.fixed.inset-0') as HTMLElement;
      expect(getComputedStyle(backdrop).display).toBe('none');
    });
  });
});
