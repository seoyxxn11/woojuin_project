import { atom } from 'jotai';

/**
 * 스테이지 헤더 제목 아래 한 줄 요약 (예: "128 memories · 12 constellations").
 *
 * 제목(워크스페이스 이름)은 네 뷰가 공유하므로 StageLayout 이 직접 읽지만,
 * 이 요약은 뷰마다 세는 대상이 달라 페이지가 올려준다. `useStageMeta` 로 쓴다.
 */
export const stageMetaAtom = atom<string | undefined>(undefined);
