import { useEffect } from 'react';
import { useSetAtom } from 'jotai';
import { stageMetaAtom } from '@/stores/stageAtoms';

/**
 * 스테이지 헤더의 요약 줄을 페이지에서 올린다.
 *
 * 언마운트 때 비우지 않는다 — memories·constellations 는 뷰가 아니라
 * 워크스페이스를 세는 값이라, 성좌에서 지도로 넘어가도 그대로 유효하다.
 * 다른 값을 쓰고 싶은 뷰는 자기 값으로 덮어쓰면 된다.
 */
export function useStageMeta(meta?: string) {
  const setMeta = useSetAtom(stageMetaAtom);

  useEffect(() => {
    setMeta(meta);
  }, [meta, setMeta]);
}
