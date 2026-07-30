import type { Item } from '@/types/item';

/**
 * 아이템의 썸네일 소스를 정한다 — 타입마다 어디서 이미지를 얻는지 다르다.
 *
 *   IMAGE → 서버가 준 접근 URL(imageUrl). s3Key 로 직접 조립하지 않는다
 *           (버킷이 비공개라 직접 접근은 403 — 서버가 URL 을 만들어 준다)
 *   URL   → 크롤링 미리보기(preview.thumbnailUrl)
 *   MEMO  → 없음(카드가 회색 줄 스켈레톤으로 그린다)
 *
 * 카드와 상세 모달이 같은 이미지를 써야 하므로 이 판단을 한 곳에 둔다.
 */
export function resolveThumbnail(item: Item): string | null {
  if (item.type === 'IMAGE') return item.imageUrl;
  if (item.type === 'URL') return item.preview.thumbnailUrl;
  return null;
}

/** 썸네일을 못 얻은 링크에 깔 브랜드 타일. 실물 로고 대신 색+이름으로 표현한다. */
export interface Brand {
  /** 타일에 쓸 짧은 이름 */
  label: string;
  /** CSS background 값 */
  background: string;
}

/**
 * 크롤링이 구조적으로 막혀 썸네일을 얻을 수 없는 쇼핑몰들.
 *
 * 이 목록에 올리는 기준은 "잠깐 실패"가 아니라 **봇 차단이 정책인 곳**이다. 일시적
 * 레이트리밋(네이버 IP 제한)은 다시 저장하면 성공하므로 브랜드 타일로 굳히면 손해다 —
 * 다만 스마트스토어는 실패율이 높아 함께 넣었다. 실제 썸네일을 얻은 아이템은 애초에
 * 이 코드를 타지 않으므로(resolveThumbnail 이 값을 준다) 성공 케이스를 망치지 않는다.
 *
 * 실물 로고 이미지를 쓰지 않는 이유: 상표 문제가 있고, 바이너리 애셋을 번들에 넣어야
 * 하고, 외부 URL 핫링크는 조용히 깨진다. 색+이름이면 "어느 쇼핑몰인지"는 똑같이 전달된다.
 *
 * host 는 접미사로 매칭한다 — m./www./link. 등 서브도메인 변종을 일일이 적지 않기 위해서다.
 */
const BRANDS: { host: string; brand: Brand }[] = [
  {
    host: 'coupang.com',
    brand: { label: '쿠팡', background: 'linear-gradient(135deg,#e3413c,#8f1f1c)' },
  },
  {
    host: 'smartstore.naver.com',
    brand: { label: '스마트스토어', background: 'linear-gradient(135deg,#22c96f,#0c7a3d)' },
  },
  {
    host: 'brand.naver.com',
    brand: { label: '브랜드스토어', background: 'linear-gradient(135deg,#22c96f,#0c7a3d)' },
  },
  {
    host: 'shopping.naver.com',
    brand: { label: '네이버쇼핑', background: 'linear-gradient(135deg,#22c96f,#0c7a3d)' },
  },
];

/**
 * 썸네일이 없는 URL 아이템에 쓸 브랜드 타일. 해당 없으면 null (카드가 기존 그라디언트 폴백).
 *
 * naver.me 는 일부러 넣지 않았다 — 지도·블로그·쇼핑을 모두 가리키는 단축 링크라
 * 쇼핑으로 단정할 수 없다.
 */
export function resolveBrand(item: Item): Brand | null {
  if (item.type !== 'URL' || !item.url) return null;
  if (item.preview.thumbnailUrl) return null; // 실제 썸네일이 있으면 브랜드 타일이 필요 없다

  let host: string;
  try {
    host = new URL(item.url).hostname.toLowerCase();
  } catch {
    return null; // 저장된 url 이 파싱 불가면 조용히 포기 (카드는 그라디언트로)
  }

  const matched = BRANDS.find(({ host: h }) => host === h || host.endsWith(`.${h}`));
  return matched?.brand ?? null;
}
