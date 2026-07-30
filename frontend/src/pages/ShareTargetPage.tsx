import { useSearchParams } from 'react-router-dom';
import { parseSharedContent } from '@/utils/sharedContent';

/**
 * OS 공유 시트에서 '우주인' 선택 시 진입하는 페이지 (FR-013)
 *
 * 파라미터 해석(어느 앱이 무엇을 어디에 담는지)은 parseSharedContent 가 전담한다.
 * 여기서는 그 결과를 보여주기만 한다.
 *
 * 쿠팡/네이버쇼핑처럼 크롤링이 막힌 곳은 공유 텍스트의 상품명이 유일한 제목 소스라,
 * 저장 시 title 을 함께 보내야 카드가 "www.coupang.com/vp/products/..." 로 남지 않는다.
 * saveUrl 이 title 을 받도록 준비돼 있다.
 *
 * TODO: 워크스페이스 선택 UI (FR-042) + saveUrl(workspaceId, url, title) 호출
 */
export default function ShareTargetPage() {
  const [params] = useSearchParams();
  const { url, title } = parseSharedContent(params);

  return (
    <main>
      <h1>저장하기</h1>
      <p>공유된 URL: {url || '(URL 없음 — 메모로 저장)'}</p>
      {title && <p>공유된 제목: {title}</p>}
    </main>
  );
}
