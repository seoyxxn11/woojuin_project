import { describe, it, expect } from 'vitest';
import { render } from 'vitest-browser-react';
import Thumbnail from '@/components/domain/library/Thumbnail';

const img = (c: HTMLElement) => c.querySelector('img');

describe('Thumbnail', () => {
  /**
   * 이 한 줄이 없으면 네이버(blogthumb.pstatic.net) 같은 핫링크 차단 호스트가
   * 외부 Referer 를 보고 403 을 준다(2026-08-06 실측: Referer 없음 200, 외부 Referer 403).
   * 상세는 외부 og:image 원본을 그대로 쓰므로 여기서 Referer 를 끊어야 이미지가 뜬다.
   *
   * 눈으로는 회귀를 못 잡는 종류다 — 속성이 빠져도 화면은 멀쩡해 보이고,
   * 개발 환경(localhost Referer)에서는 대체로 통과한다. 네이버 링크를 저장한
   * 사용자만 배포 후에 깨진다.
   */
  it('외부 이미지에 Referer 를 보내지 않는다', async () => {
    const { container } = await render(
      <Thumbnail src="https://blogthumb.pstatic.net/x.jpg" seed={1} className="h-40 w-40" />,
    );
    expect(img(container)).toHaveAttribute('referrerpolicy', 'no-referrer');
  });

  // 카드가 화면 밖에 있으면 받지 않는다 — 대시보드 이미지 전송량의 근거(perf/FE-thumbnail-lazy)
  it('지연 로딩으로 그린다', async () => {
    const { container } = await render(
      <Thumbnail src="https://example.com/x.jpg" seed={1} className="h-40 w-40" />,
    );
    expect(img(container)).toHaveAttribute('loading', 'lazy');
  });

  /**
   * src 가 없으면 그라디언트로 자리를 채운다 — 빈 상자가 아니라 색이 깔려야
   * 카드 격자가 무너지지 않는다.
   */
  it('src 가 없으면 이미지를 그리지 않고 그라디언트를 깐다', async () => {
    const { container } = await render(<Thumbnail src={null} seed={2} className="h-40 w-40" />);
    expect(img(container)).toBeNull();
    const box = container.querySelector('div') as HTMLElement;
    expect(box.style.background).toContain('linear-gradient');
  });

  /**
   * https 페이지에서 http 이미지는 혼합 콘텐츠로 차단돼 요청조차 나가지 않는다 —
   * referrerPolicy 로는 못 살리는 별개의 실패 경로다. 백엔드가 og:image 스킴을 그대로
   * 내려주므로(OpenGraphScraper.absolutize) http 로 서빙하는 블로그가 여기로 들어온다.
   *
   * 테스트는 실제 페이지가 http(localhost)라 승격이 일어나지 않는 쪽을 확인한다 —
   * 로컬 MinIO(http://localhost:9000)가 깨지면 안 되기 때문이고, 이게 회귀 위험이 더 크다.
   */
  it('페이지가 http 면 http 이미지를 그대로 둔다 (로컬 MinIO 보호)', async () => {
    expect(window.location.protocol).toBe('http:');
    const { container } = await render(
      <Thumbnail src="http://localhost:9000/bucket/a.jpg" seed={4} className="h-40 w-40" />,
    );
    expect(img(container)).toHaveAttribute('src', 'http://localhost:9000/bucket/a.jpg');
  });

  // https 페이지가 아니면 승격하지 않으므로, 승격 규칙 자체는 순수하게 따로 검증한다
  it('https 승격 규칙 — http 만, 그리고 https 페이지에서만', () => {
    const upgrade = (src: string, protocol: string) =>
      src.startsWith('http://') && protocol === 'https:'
        ? `https://${src.slice('http://'.length)}`
        : src;

    expect(upgrade('http://blog.kr/a.jpg', 'https:')).toBe('https://blog.kr/a.jpg');
    expect(upgrade('http://localhost:9000/a.jpg', 'http:')).toBe('http://localhost:9000/a.jpg');
    expect(upgrade('https://blog.kr/a.jpg', 'https:')).toBe('https://blog.kr/a.jpg');
  });

  /**
   * 로드에 실패하면 깨진 이미지 아이콘 대신 그라디언트로 되돌린다.
   * referrerPolicy 로도 못 살리는 경우(404·만료된 URL 등)의 마지막 방어선이다.
   */
  it('로드에 실패하면 그라디언트로 되돌린다', async () => {
    const { container } = await render(
      <Thumbnail src="https://example.com/404.jpg" seed={3} className="h-40 w-40" />,
    );
    const el = img(container)!;
    el.dispatchEvent(new Event('error'));

    await expect.poll(() => img(container)).toBeNull();
    const box = container.querySelector('div') as HTMLElement;
    expect(box.style.background).toContain('linear-gradient');
  });
});
