import { TYPE_LABEL } from '@/stores/mock/universe';
import type { ScreenPosition, StarNode } from '@/utils/scene';

interface StarTooltipProps {
  node: StarNode;
  position: ScreenPosition;
  onClick: () => void;
  onPointerOverChange: (over: boolean) => void;
}

/**
 * 별 호버 툴팁 — 목업 `.tooltip`.
 * 별자리 중심은 간단히(개수만), 저장물은 제목까지 보여준다.
 */
const StarTooltip = ({ node, position, onClick, onPointerOverChange }: StarTooltipProps) => {
  const { isHub, hub, star, categoryName, cssColor } = node;

  return (
    <div
      role="tooltip"
      onClick={onClick}
      onMouseEnter={() => onPointerOverChange(true)}
      onMouseLeave={() => onPointerOverChange(false)}
      style={{ left: position.x, top: position.y }}
      className="pointer-events-auto absolute z-[6] w-[238px] -translate-x-1/2 -translate-y-[118%] cursor-pointer rounded-[13px] border border-border bg-[rgba(23,24,29,.92)] px-[15px] py-[13px] shadow-tooltip backdrop-blur-[18px]"
    >
      <span className="inline-flex items-center gap-1.5 rounded-pill bg-surface-3 px-[9px] py-[3px] text-[11px] font-bold">
        <span
          className="h-1.5 w-1.5 shrink-0 rounded-full"
          style={{ backgroundColor: cssColor }}
          aria-hidden="true"
        />
        {categoryName ?? '미분류'}
        {!isHub && star && (
          <span className="font-semibold text-text-3">· {TYPE_LABEL[star.type]}</span>
        )}
      </span>

      {isHub && hub ? (
        <div className="mt-1 text-[11px] text-text-3">
          {hub.itemCount} memories · 클릭하면 대시보드
        </div>
      ) : (
        star && (
          <>
            <div className="mt-2 text-[13.5px] font-bold text-text-1">{star.title}</div>
            <div className="mt-2 text-[11px] text-text-3">
              {star.type === 'URL' ? '클릭하면 링크로 이동' : '클릭하여 열기'}
            </div>
          </>
        )
      )}
    </div>
  );
};

export default StarTooltip;
