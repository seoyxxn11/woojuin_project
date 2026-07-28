import { describe, it, expect } from 'vitest';
import { render } from 'vitest-browser-react';
import { page } from 'vitest/browser';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TabBar from '@/components/domain/nav/TabBar';
import { getMobileSize } from '@/constants/breakpoints';

/** useUser 가 서버 상태를 쓰므로 QueryClientProvider 가 필요하다 */
const renderTabBar = (path = '/workspace/3/universe') =>
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter initialEntries={[path]}>
        <TabBar />
      </MemoryRouter>
    </QueryClientProvider>,
  );

const nav = (c: HTMLElement) => c.querySelector('nav')!;
const tabs = (c: HTMLElement) => [...nav(c).querySelectorAll('a')];
const tab = (c: HTMLElement, label: string) =>
  tabs(c).find((t) => t.getAttribute('aria-label') === label)!;

describe('TabBar', () => {
  it('탭 다섯 개를 순서대로 보여준다', async () => {
    const { container } = await renderTabBar();
    expect(tabs(container).map((t) => t.getAttribute('aria-label'))).toEqual([
      '우주',
      '보관함',
      '지도',
      '마이',
      '휴지통',
    ]);
  });

  describe('목적지 — 두 종류가 섞여 있다', () => {
    it('뷰 셋은 지금 보고 있는 워크스페이스에 붙는다', async () => {
      const { container } = await renderTabBar('/workspace/3/universe');
      expect(tab(container, '우주')).toHaveAttribute('href', '/workspace/3/universe');
      expect(tab(container, '보관함')).toHaveAttribute('href', '/workspace/3/library');
      expect(tab(container, '지도')).toHaveAttribute('href', '/workspace/3/map');
    });

    it('마이·휴지통은 워크스페이스와 무관한 절대 경로다', async () => {
      // 사이드바의 휴지통과 같은 경로여야 한다
      const { container } = await renderTabBar('/workspace/3/universe');
      expect(tab(container, '마이')).toHaveAttribute('href', '/my');
      expect(tab(container, '휴지통')).toHaveAttribute('href', '/trash');
    });
  });

  describe('선택 표시', () => {
    it('현재 경로의 탭만 켜진다', async () => {
      const { container } = await renderTabBar('/workspace/3/map');
      const current = tabs(container).filter((t) => t.getAttribute('aria-current') === 'page');
      expect(current).toHaveLength(1);
      expect(current[0].getAttribute('aria-label')).toBe('지도');
    });

    it('하위 경로에서도 켜진 채로 있다', async () => {
      // 보관함에서 폴더로 들어가도 탭이 꺼지면 안 된다
      const { container } = await renderTabBar('/workspace/3/library/7');
      expect(tab(container, '보관함')).toHaveAttribute('aria-current', 'page');
    });
  });

  describe('노출 — 컴포넌트가 스스로 정한다', () => {
    // 호출부가 sm:hidden 을 안 붙여도 데스크톱에서 보이면 안 된다
    it('모바일에서는 보인다', async () => {
      await page.viewport(getMobileSize() - 1, 800);
      const { container } = await renderTabBar();
      expect(getComputedStyle(nav(container)).display).not.toBe('none');
    });

    it('데스크톱에서는 감춰진다', async () => {
      await page.viewport(getMobileSize(), 800);
      const { container } = await renderTabBar();
      expect(getComputedStyle(nav(container)).display).toBe('none');

      await page.viewport(1280, 800);
    });
  });
});
