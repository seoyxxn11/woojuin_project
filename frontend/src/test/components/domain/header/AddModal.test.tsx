import { describe, it, expect } from 'vitest';
import { render } from 'vitest-browser-react';
import { userEvent } from 'vitest/browser';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AddModal from '@/components/domain/header/AddModal';

/** 폼들이 useParams(workspaceId)·useQueryClient 를 쓰므로 라우트와 쿼리 클라이언트가 필요하다 */
const setup = () =>
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}
    >
      <MemoryRouter initialEntries={['/workspace/7/universe']}>
        <Routes>
          <Route path="/workspace/:workspaceId/universe" element={<AddModal onDone={() => {}} />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

const tab = (c: HTMLElement, label: string) =>
  [...c.querySelectorAll('[role="tab"]')].find((t) => t.textContent === label) as HTMLButtonElement;

describe('AddModal', () => {
  it('탭 세 개를 보여준다', async () => {
    const { container } = await setup();
    const labels = [...container.querySelectorAll('[role="tab"]')].map((t) => t.textContent);
    expect(labels).toEqual(['링크', '사진', '텍스트']);
  });

  describe('탭에 맞는 폼을 보여준다', () => {
    it('기본은 링크 — url 입력', async () => {
      const { container } = await setup();
      expect(container.querySelector('input[type="url"]')).not.toBeNull();
    });

    it('사진 — 이미지 파일 선택', async () => {
      const { container } = await setup();
      await userEvent.click(tab(container, '사진'));

      const file = container.querySelector<HTMLInputElement>('input[type="file"]');
      expect(file).not.toBeNull();
      // 이미지가 아닌 파일이 섞이면 서버에서 걸러야 하므로 입력 단계에서 제한한다
      expect(file).toHaveAttribute('accept', 'image/*');
      expect(container.querySelector('input[type="url"]')).toBeNull();
    });

    it('텍스트 — 여러 줄 입력', async () => {
      const { container } = await setup();
      await userEvent.click(tab(container, '텍스트'));

      expect(container.querySelector('textarea')).not.toBeNull();
      // 요청 필드가 content 뿐이라 제목 입력은 두지 않는다
      expect(container.querySelector('input[type="text"]')).toBeNull();
    });
  });

  describe('선택 상태', () => {
    it('고른 탭만 aria-selected 다', async () => {
      const { container } = await setup();
      await userEvent.click(tab(container, '텍스트'));

      expect(tab(container, '텍스트')).toHaveAttribute('aria-selected', 'true');
      expect(tab(container, '링크')).toHaveAttribute('aria-selected', 'false');
    });
  });

  describe('폼끼리 상태가 섞이지 않는다', () => {
    it('탭을 옮겼다 돌아오면 입력이 남아 있지 않다', async () => {
      // 폼을 컴포넌트로 나눈 이유 — 각자 자기 상태를 갖고 언마운트되며 정리된다
      const { container } = await setup();

      const url = container.querySelector<HTMLInputElement>('input[type="url"]')!;
      await userEvent.fill(url, 'https://example.com');
      expect(url.value).toBe('https://example.com');

      await userEvent.click(tab(container, '텍스트'));
      await userEvent.click(tab(container, '링크'));

      expect(container.querySelector<HTMLInputElement>('input[type="url"]')!.value).toBe('');
    });
  });

  describe('제출 조건', () => {
    it('사진은 파일을 고르기 전엔 저장할 수 없다', async () => {
      const { container } = await setup();
      await userEvent.click(tab(container, '사진'));
      expect(container.querySelector<HTMLButtonElement>('button[type="submit"]')!.disabled).toBe(
        true,
      );
    });

    it('텍스트는 내용이 비면 저장할 수 없다', async () => {
      const { container } = await setup();
      await userEvent.click(tab(container, '텍스트'));
      const submit = container.querySelector<HTMLButtonElement>('button[type="submit"]')!;
      expect(submit.disabled).toBe(true);

      // 공백만 넣어도 여전히 잠겨 있어야 한다
      await userEvent.fill(container.querySelector('textarea')!, '   ');
      expect(submit.disabled).toBe(true);
    });

    it('텍스트에 내용을 넣으면 저장할 수 있다', async () => {
      const { container } = await setup();
      await userEvent.click(tab(container, '텍스트'));
      await userEvent.fill(container.querySelector('textarea')!, '메모 내용');
      expect(container.querySelector<HTMLButtonElement>('button[type="submit"]')!.disabled).toBe(
        false,
      );
    });
  });
});
