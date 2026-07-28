import { describe, it, expect } from 'vitest';
import { render } from 'vitest-browser-react';
import { MemoryRouter } from 'react-router-dom';
import { userEvent } from 'vitest/browser';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SideBar from '@/components/domain/nav/SideBar';
import type { Workspace } from '@/services/workspaces';

/**
 * 워크스페이스 목록은 서버에서 온다. 개인 스페이스 id 는 USER_MOCK 의 1 이므로
 * id 1 을 개인으로 두면 나머지 둘만 Workspaces 목록에 남는다(useSpaces 규칙).
 */
const WORKSPACES: Workspace[] = [
  { id: 1, name: 'Personal Space', type: 'PERSONAL', role: 'OWNER' },
  { id: 2, name: '몽골 여행', type: 'TEAM', role: 'OWNER' },
  { id: 3, name: '팀 프로젝트', type: 'TEAM', role: 'MEMBER' },
];

/**
 * useUser·useSpaces 가 서버 상태(useQuery)를 쓰므로 QueryClientProvider 가 필요하다.
 *
 * 목록은 캐시에 미리 넣어 첫 렌더부터 보이게 한다 — 요청이 끝나길 기다리지 않아도 된다.
 * 프로필은 일부러 비워 둔다. 요청이 실패하면 useUser 가 USER_MOCK 으로 떨어지는데,
 * 아래 단언들(홍길동·저장 공간)이 기대하는 값이 바로 그 목업이다.
 */
const renderSideBar = (path = '/workspace/1') => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  queryClient.setQueryData(['workspaces'], WORKSPACES);

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <SideBar />
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

const aside = (c: HTMLElement) => c.querySelector('aside') as HTMLElement;
const rowByText = (c: HTMLElement, text: string) =>
  [...c.querySelectorAll('a,button')].find((e) => e.textContent?.includes(text)) as HTMLElement;
const dotIn = (row: HTMLElement) => row.querySelector('span.bg-current');
const toggleBtn = (c: HTMLElement) =>
  [...c.querySelectorAll('button')].find((b) =>
    /사이드바/.test(b.getAttribute('aria-label') ?? ''),
  ) as HTMLElement;

describe('SideBar (통합)', () => {
  it('브랜드·네비·워크스페이스·저장공간·유저를 모두 렌더한다', async () => {
    const { container } = await renderSideBar();
    const text = aside(container).textContent ?? '';
    for (const part of [
      'WooJuIn',
      'Personal Space',
      '휴지통',
      'SPACE',
      'Workspaces',
      '몽골 여행',
    ]) {
      expect(text).toContain(part);
    }
    expect(text).toContain('저장 공간');
    expect(text).toContain('홍길동');
  });

  describe('항목 선택 — Context 가 하위 컴포넌트를 넘나든다', () => {
    it('개인 스페이스에 있으면 Personal Space 가 선택돼 보인다', async () => {
      // 선택은 클릭이 아니라 현재 URL 이 정한다 — /workspace/1 이 개인 스페이스다
      const { container } = await renderSideBar('/workspace/1');
      expect(dotIn(rowByText(container, 'Personal Space'))).not.toBeNull();
      expect(dotIn(rowByText(container, '몽골 여행'))).toBeNull();
    });

    it('워크스페이스를 누르면 고정 네비의 선택이 해제된다', async () => {
      // FixedNav 와 WorkspaceNav 는 서로 다른 컴포넌트 — Context 로 상태를 공유한다
      const { container } = await renderSideBar();
      await userEvent.click(rowByText(container, '몽골 여행'));
      expect(dotIn(rowByText(container, '몽골 여행'))).not.toBeNull();
      expect(dotIn(rowByText(container, 'Personal Space'))).toBeNull();
    });

    it('선택 표시는 항상 하나뿐이다', async () => {
      // 이동해도 점이 늘어나면 안 된다 (휴지통은 아직 경로가 없어 점 대상이 아니다)
      const { container } = await renderSideBar('/workspace/1');
      expect(aside(container).querySelectorAll('span.bg-current')).toHaveLength(1);

      await userEvent.click(rowByText(container, '몽골 여행'));
      expect(aside(container).querySelectorAll('span.bg-current')).toHaveLength(1);
    });
  });

  describe('접기 — 폭과 노출이 함께 바뀐다', () => {
    it('기본은 300px, 접으면 72px 이 된다', async () => {
      const { container } = await renderSideBar();
      const width = () => aside(container).getBoundingClientRect().width;
      expect(width()).toBeCloseTo(300, 0);

      await userEvent.click(toggleBtn(container));
      // transition-[width] duration-200 이라 전환이 끝날 때까지 기다린다
      await expect.poll(width).toBeCloseTo(72, 0);
    });

    it('접으면 저장 공간과 유저 정보가 사라진다', async () => {
      const { container } = await renderSideBar();
      await userEvent.click(toggleBtn(container));
      const text = aside(container).textContent ?? '';
      expect(text).not.toContain('저장 공간');
      expect(text).not.toContain('dngusdlqwkd@gmail.com');
    });
  });

  describe('워크스페이스 목록', () => {
    it('Workspaces 를 누르면 목록이 접힌다', async () => {
      const { container } = await renderSideBar();
      await userEvent.click(rowByText(container, 'Workspaces'));
      expect(aside(container).textContent).not.toContain('몽골 여행');
    });

    it('하위 항목은 4px 들여쓰되 오른쪽 끝은 맞춘다', async () => {
      // w-full + ml-1 이면 폭이 안 줄어 오른쪽이 삐져나온다 — 컨테이너 패딩으로 처리해야 한다
      const { container } = await renderSideBar();
      const parent = rowByText(container, 'Workspaces').getBoundingClientRect();
      const child = rowByText(container, '몽골 여행').getBoundingClientRect();

      expect(child.left - parent.left).toBeCloseTo(4, 0);
      expect(child.right).toBeCloseTo(parent.right, 0);
    });
  });

  describe('내비게이션', () => {
    it('이동 항목은 링크, 동작 항목은 버튼이다', async () => {
      const { container } = await renderSideBar();
      expect(rowByText(container, 'Personal Space').tagName).toBe('A');
      expect(rowByText(container, '몽골 여행').tagName).toBe('A');
      // 목록 토글·새 워크스페이스는 이동이 아니다
      expect(rowByText(container, 'Workspaces').tagName).toBe('BUTTON');
      expect(rowByText(container, 'New workspace').tagName).toBe('BUTTON');
    });

    it('휴지통은 워크스페이스와 무관한 /trash 로 간다', async () => {
      // 모바일 탭바와 같은 경로다 — 한쪽만 바뀌면 두 내비가 다른 곳을 가리킨다
      const { container } = await renderSideBar();
      const trash = rowByText(container, '휴지통');

      expect(trash.tagName).toBe('A');
      expect(trash).toHaveAttribute('href', '/trash');
    });

    it('휴지통 화면에서는 휴지통에만 선택 표시가 뜬다', async () => {
      const { container } = await renderSideBar('/trash');

      expect(dotIn(rowByText(container, '휴지통'))).not.toBeNull();
      expect(dotIn(rowByText(container, 'Personal Space'))).toBeNull();
    });
  });
});
