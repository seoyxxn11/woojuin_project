import { describe, expect, it } from 'vitest';
import { parseSharedContent } from '@/utils/sharedContent';

/** 공유 시트 파라미터를 URLSearchParams 로 만든다 (실제 진입은 /share-target?...) */
const share = (params: Record<string, string>) => new URLSearchParams(params);

describe('parseSharedContent', () => {
  describe('URL 추출', () => {
    it('url 파라미터로 오면 그대로 쓴다 (카톡·크롬·유튜브)', () => {
      const { url } = parseSharedContent(share({ url: 'https://example.com/a' }));
      expect(url).toBe('https://example.com/a');
    });

    it('text 에 섞여 오면 정규식으로 뽑는다 (인스타·트위터)', () => {
      const { url } = parseSharedContent(share({ text: '이거 봐 https://example.com/a 대박' }));
      expect(url).toBe('https://example.com/a');
    });

    it('URL 이 아예 없으면 빈 문자열 (호출부가 메모로 폴백)', () => {
      const { url } = parseSharedContent(share({ text: '그냥 메모' }));
      expect(url).toBe('');
    });
  });

  describe('제목 추출', () => {
    it('title 파라미터가 있으면 그것을 쓴다', () => {
      const { title } = parseSharedContent(
        share({ title: '무선 이어폰 블루투스 5.3', url: 'https://example.com' }),
      );
      expect(title).toBe('무선 이어폰 블루투스 5.3');
    });

    // 쿠팡이 이 경로다 — title 은 비어 있고 text 에 상품명+URL 이 함께 온다
    it('title 이 비면 text 에서 URL 을 걷어낸 나머지를 쓴다', () => {
      const { title } = parseSharedContent(
        share({
          text: '무선 이어폰 블루투스 5.3 39,900원 https://www.coupang.com/vp/products/123',
        }),
      );
      expect(title).toBe('무선 이어폰 블루투스 5.3 39,900원');
    });

    it('줄바꿈·연속 공백은 한 칸으로 눕힌다', () => {
      const { title } = parseSharedContent(
        share({ text: '무선 이어폰\n\n39,900원   https://example.com' }),
      );
      expect(title).toBe('무선 이어폰 39,900원');
    });

    it('쓸 게 없으면 null — 서버가 크롤링 제목을 쓰도록', () => {
      const { title } = parseSharedContent(share({ url: 'https://example.com' }));
      expect(title).toBeNull();
    });

    // 빈 문자열을 서버로 보내면 크롤링 제목을 막아버린다 → 반드시 null 이어야 한다
    it('title 이 공백뿐이어도 null', () => {
      const { title } = parseSharedContent(share({ title: '   ', url: 'https://example.com' }));
      expect(title).toBeNull();
    });

    it('URL 만 남으면 제목으로 쓰지 않는다 (링크만 여러 개 공유한 경우)', () => {
      const { title } = parseSharedContent(
        share({ text: 'https://example.com/a https://example.com/b' }),
      );
      expect(title).toBeNull();
    });

    it('호스트명 꼴이면 제목으로 쓰지 않는다 (서버 host+path 폴백이 더 낫다)', () => {
      const { title } = parseSharedContent(
        share({ title: 'www.coupang.com', url: 'https://www.coupang.com/vp/products/123' }),
      );
      expect(title).toBeNull();
    });
  });
});
