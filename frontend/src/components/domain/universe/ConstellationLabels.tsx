import type { LabelPosition } from '@/utils/scene';

interface ConstellationLabelsProps {
  labels: LabelPosition[];
  onSelect: (categoryId: number) => void;
}

/**
 * 별자리 이름 오버레이 — 목업 `.clabel`.
 * 3D 좌표를 화면 좌표로 투영한 값을 매 프레임 받아 위치만 갱신한다.
 * 카메라 뒤로 돌아간 라벨은 opacity 0 으로 감춘다(레이아웃은 유지).
 */
const ConstellationLabels = ({ labels, onSelect }: ConstellationLabelsProps) => (
  <div className="pointer-events-none absolute inset-0 z-[4]">
    {labels.map((label) => (
      <button
        key={label.categoryId}
        type="button"
        onClick={() => onSelect(label.categoryId)}
        style={{ left: label.x, top: label.y, opacity: label.visible ? 1 : 0 }}
        className="pointer-events-auto absolute -translate-y-1/2 cursor-pointer whitespace-nowrap text-[12.5px] font-semibold text-[rgba(232,234,238,.92)] transition-opacity duration-200 [text-shadow:0_1px_8px_rgba(0,0,0,.95)]"
      >
        {label.name}
      </button>
    ))}
  </div>
);

export default ConstellationLabels;
