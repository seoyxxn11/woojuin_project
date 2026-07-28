import type { ReactNode } from 'react';
import ViewBar from './ViewBar';

interface StageHeaderProps {
  /** 워크스페이스 이름 */
  title: string;
  /** 제목 아래 한 줄 요약 (예: "128 memories · 12 constellations") */
  meta?: string;
  /**
   * 뷰바 왼쪽에 붙는 자리 — 멤버 아바타·알림·공유가 들어간다.
   * 셋 다 API 가 아직 없어 비워둔 상태다.
   */
  actions?: ReactNode;
}

/**
 * 스테이지(성좌·대시보드·지도) 위에 떠 있는 상단 헤더.
 *
 * 캔버스를 덮고 있으므로 기본은 pointer-events-none 이고,
 * 실제로 눌러야 하는 오른쪽 묶음만 다시 켠다. 그래야 제목 옆 빈 공간에서도
 * 별을 드래그해 우주를 돌릴 수 있다.
 */
const StageHeader = ({ title, meta, actions }: StageHeaderProps) => (
  <header className="pointer-events-none absolute inset-x-0 top-0 z-[5] flex items-start justify-between gap-4 px-5 pt-5 desktop:px-[34px] desktop:pt-[26px]">
    <div className="min-w-0">
      <h1 className="truncate text-2xl font-extrabold tracking-[-0.01em] text-text-1 desktop:text-[30px]">
        {title}
      </h1>
      {meta && <p className="mt-[3px] truncate text-xs text-text-2 desktop:text-sm">{meta}</p>}
    </div>

    <div className="pointer-events-auto flex shrink-0 items-center gap-2">
      {actions}
      <ViewBar />
    </div>
  </header>
);

export default StageHeader;
