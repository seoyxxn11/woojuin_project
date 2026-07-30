import { describe, expect, it } from 'vitest';
import type { Item } from '@/types/item';
import { resolveBrand, resolveThumbnail } from '@/utils/itemThumbnail';

const urlItem = (url: string | null, thumbnailUrl: string | null = null): Item =>
  ({
    itemId: 1,
    type: 'URL',
    status: 'PARTIAL',
    title: '무선 이어폰',
    url,
    summary: null,
    preview: { thumbnailUrl, description: null },
    imageUrl: null,
    categories: [],
    favorite: false,
    createdAt: '2026-07-30T00:00:00Z',
    deletedAt: null,
  }) as Item;

describe('resolveBrand', () => {
  it('쿠팡 링크는 쿠팡 타일', () => {
    expect(resolveBrand(urlItem('https://www.coupang.com/vp/products/123'))?.label).toBe('쿠팡');
  });

  it('서브도메인 변종도 잡는다 (m./link.)', () => {
    expect(resolveBrand(urlItem('https://m.coupang.com/vm/products/9'))?.label).toBe('쿠팡');
    expect(resolveBrand(urlItem('https://link.coupang.com/a/abcdef'))?.label).toBe('쿠팡');
  });

  it('스마트스토어는 스마트스토어 타일', () => {
    expect(resolveBrand(urlItem('https://smartstore.naver.com/shop/products/7'))?.label).toBe(
      '스마트스토어',
    );
  });

  // 실제 썸네일이 있으면 브랜드 타일이 이미지를 가려선 안 된다
  it('썸네일을 이미 얻었으면 브랜드 타일을 쓰지 않는다', () => {
    expect(
      resolveBrand(urlItem('https://www.coupang.com/vp/products/1', 'https://img/a.jpg')),
    ).toBeNull();
  });

  it('목록에 없는 호스트는 null (기존 그라디언트 폴백)', () => {
    expect(resolveBrand(urlItem('https://example.com/a'))).toBeNull();
  });

  // 지도·블로그·쇼핑을 모두 가리키는 단축 링크라 쇼핑으로 단정할 수 없다
  it('naver.me 단축 링크는 쇼핑으로 단정하지 않는다', () => {
    expect(resolveBrand(urlItem('https://naver.me/abcd1234'))).toBeNull();
  });

  // "notcoupang.com" 이 접미사 매칭에 걸리면 안 된다
  it('호스트 접미사 매칭은 점 경계를 지킨다', () => {
    expect(resolveBrand(urlItem('https://notcoupang.com/x'))).toBeNull();
  });

  it('url 이 없거나 파싱 불가면 null', () => {
    expect(resolveBrand(urlItem(null))).toBeNull();
    expect(resolveBrand(urlItem('그냥 문자열'))).toBeNull();
  });

  it('URL 타입이 아니면 null', () => {
    const memo = { ...urlItem('https://www.coupang.com/vp/products/1'), type: 'MEMO' } as Item;
    expect(resolveBrand(memo)).toBeNull();
  });
});

describe('resolveThumbnail', () => {
  it('URL 은 크롤링 미리보기를 쓴다', () => {
    expect(resolveThumbnail(urlItem('https://example.com', 'https://img/a.jpg'))).toBe(
      'https://img/a.jpg',
    );
  });

  it('미리보기가 없으면 null (브랜드·그라디언트 폴백은 컴포넌트가 판단)', () => {
    expect(resolveThumbnail(urlItem('https://example.com'))).toBeNull();
  });
});
