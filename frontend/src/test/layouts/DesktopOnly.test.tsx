import { describe, it, expect } from 'vitest';
import { render } from 'vitest-browser-react';
import { page } from 'vitest/browser';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import DesktopOnly from '@/layouts/DesktopOnly';
import { getMobileSize } from '@/constants/breakpoints';

/** 실제 라우터에서와 같은 위치 — /workspace/:workspaceId 아래에 둔다 */
const renderGuard = (path = '/workspace/3/canvas') =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/workspace/:workspaceId" element={<DesktopOnly />}>
          <Route path="canvas" element={<p>캔버스 내용</p>} />
        </Route>
        <Route path="/workspace/:workspaceId/universe" element={<p>성좌 내용</p>} />
      </Routes>
    </MemoryRouter>,
  );

describe('DesktopOnly', () => {
  it('데스크톱에서는 그대로 보여준다', async () => {
    await page.viewport(getMobileSize(), 800);
    const { container } = await renderGuard();
    expect(container.textContent).toContain('캔버스 내용');
  });

  it('모바일에서는 성좌로 돌려보낸다', async () => {
    // ViewBar 가 감춰져도 링크를 직접 열 수 있어 가드가 필요하다
    await page.viewport(getMobileSize() - 1, 800);
    const { container } = await renderGuard();

    expect(container.textContent).toContain('성좌 내용');
    expect(container.textContent).not.toContain('캔버스 내용');
  });

  it('원래 있던 워크스페이스로 돌아간다', async () => {
    // 하드코딩된 /universe 로 보내면 남의 워크스페이스로 튕긴다
    await page.viewport(getMobileSize() - 1, 800);
    const { container } = await renderGuard('/workspace/12/canvas');
    expect(container.textContent).toContain('성좌 내용');

    await page.viewport(1280, 800);
  });
});
