import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from '@/services/client';
import { saveImage, saveMemo, saveUrl } from '@/services/items';

vi.mock('@/services/client', () => ({
  api: { post: vi.fn(), get: vi.fn() },
}));

const post = vi.mocked(api.post);

/** post 로 넘어간 [경로, 본문] */
const lastCall = () => post.mock.calls[0] as unknown as [string, unknown];

beforeEach(() => {
  post.mockReset();
  post.mockResolvedValue({
    data: { data: { itemId: 1, status: 'PROCESSING', createdAt: '2026-07-23T10:00:00+09:00' } },
  });
});

describe('저장 항목 생성', () => {
  it('세 타입 모두 같은 경로로 보낸다', async () => {
    await saveUrl(7, 'https://example.com');
    expect(lastCall()[0]).toBe('/workspaces/7/items');
  });

  describe('URL — JSON', () => {
    it('type 과 url 만 담는다', async () => {
      // 명세: URL 은 url 필수 · content 금지
      await saveUrl(7, 'https://example.com');
      expect(lastCall()[1]).toEqual({ type: 'URL', url: 'https://example.com' });
    });
  });

  describe('MEMO — JSON', () => {
    it('type 과 content 만 담는다', async () => {
      // 명세: MEMO 는 content 필수 · url 금지
      await saveMemo(7, '메모 내용');
      expect(lastCall()[1]).toEqual({ type: 'MEMO', content: '메모 내용' });
    });
  });

  describe('IMAGE — multipart', () => {
    const file = () => new File(['x'], 'photo.png', { type: 'image/png' });

    it('FormData 로 보낸다', async () => {
      // 일반 객체로 넘기면 axios 가 JSON 으로 직렬화해 서버가 400 을 준다
      await saveImage(7, file());
      expect(lastCall()[1]).toBeInstanceOf(FormData);
    });

    it('파트 이름은 file 이다', async () => {
      await saveImage(7, file());
      const body = lastCall()[1] as FormData;
      expect(body.get('file')).toBeInstanceOf(File);
      expect((body.get('file') as File).name).toBe('photo.png');
    });

    it('Content-Type 을 직접 지정하지 않는다', async () => {
      // 직접 넣으면 boundary 가 빠져 서버 파싱이 깨진다 — 브라우저가 붙이게 둔다
      await saveImage(7, file());
      const config = post.mock.calls[0][2] as { headers?: Record<string, string> } | undefined;
      expect(config?.headers?.['Content-Type']).toBeUndefined();
    });
  });

  it('서버가 준 생성 결과를 그대로 돌려준다', async () => {
    const result = await saveUrl(7, 'https://example.com');
    expect(result).toEqual({
      itemId: 1,
      status: 'PROCESSING',
      createdAt: '2026-07-23T10:00:00+09:00',
    });
  });
});
