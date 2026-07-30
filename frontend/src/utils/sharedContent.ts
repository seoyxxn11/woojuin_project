/**
 * OS 공유 시트가 넘긴 파라미터에서 URL 과 제목을 뽑는다 (FR-013).
 *
 * manifest.share_target 이 `title`·`text`·`url` 세 개를 받는데, 앱마다 어디에 무엇을
 * 담는지가 다르다 —
 *
 *   카톡/크롬/유튜브  → url 에 깔끔하게
 *   인스타/트위터      → text 에 URL 이 섞여서
 *   쿠팡/네이버쇼핑    → text 에 "상품명 ... URL" 형태로 (title 은 비어 있기도 하다)
 *
 * 마지막 케이스가 이 함수의 존재 이유다. 쿠팡은 봇을 막아 서버가 제목을 크롤링할 수
 * 없는데, 공유 텍스트에는 상품명이 들어 있다. 그걸 건져서 저장 요청에 함께 실어 보내면
 * 크롤링 실패와 무관하게 카드에 상품명이 뜬다.
 */

const URL_REGEX = /https?:\/\/[^\s]+/;

export interface SharedContent {
  /** 저장할 URL. 못 찾으면 빈 문자열 (호출부가 메모로 폴백) */
  url: string;
  /** 공유 시트가 준 제목. 쓸 만한 게 없으면 null — 서버가 크롤링 제목을 쓴다 */
  title: string | null;
}

/**
 * title 로 쓸 만한 값인지. 걸러내지 않으면 서버에서 크롤링 제목을 막아버리는
 * 쓰레기 제목이 그대로 굳는다(백엔드 Item.applyPreview 는 title 이 있으면 안 덮어쓴다).
 *
 * 버리는 것:
 *  - 빈 값
 *  - URL 만 남은 것 (text 에서 URL 을 지웠는데 또 URL 이면 링크 나열이었던 경우)
 *  - 호스트명처럼 보이는 것 (서버의 host+path 폴백이 더 나은 정보를 준다)
 */
function isUsableTitle(value: string): boolean {
  if (value.length === 0) return false;
  if (URL_REGEX.test(value)) return false;
  // "www.coupang.com" 같이 공백 없는 도메인 꼴 — 정보량이 서버 폴백과 같거나 적다
  if (!value.includes(' ') && /\.[a-z]{2,}$/i.test(value)) return false;
  return true;
}

/** 줄바꿈·연속 공백을 한 칸으로 눕힌다. 제목은 한 줄로 보여지므로. */
function collapseWhitespace(value: string): string {
  return value.replace(/\s+/g, ' ').trim();
}

export function parseSharedContent(params: URLSearchParams): SharedContent {
  const rawUrl = params.get('url');
  const text = params.get('text') ?? '';
  const rawTitle = params.get('title') ?? '';

  const url = rawUrl ?? text.match(URL_REGEX)?.[0] ?? '';

  // title 파라미터가 우선. 비어 있으면 text 에서 URL 을 걷어낸 나머지를 쓴다 —
  // 쿠팡이 이 경로다.
  const candidates = [rawTitle, text.replace(URL_REGEX, '')].map(collapseWhitespace);
  const title = candidates.find(isUsableTitle) ?? null;

  return { url, title };
}
