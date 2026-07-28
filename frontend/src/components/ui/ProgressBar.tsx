interface ProgressBarProps {
  value: number;
  max: number;
  /** 좌측 라벨. 생략하면 상단 행 없이 막대만 그린다 */
  label?: string;
  /** 값 뒤에 붙는 단위 (예: GB) */
  unit?: string;
}

/** 라벨 + 사용량 텍스트 + 진행 막대 */
const ProgressBar = ({ value, max, label, unit }: ProgressBarProps) => {
  const percent = max > 0 ? Math.min(100, Math.max(0, Math.round((value / max) * 100))) : 0;

  return (
    <div>
      {label && (
        <div className="flex justify-between items-center mb-[7px] text-[11.5px] text-text-3">
          <span>{label}</span>
          <span className="text-text-2 tabular-nums">
            {value} / {max}
            {unit && ` ${unit}`}
          </span>
        </div>
      )}
      <div
        className="h-[5px] rounded-full bg-surface-3 overflow-hidden"
        role="progressbar"
        aria-label={label}
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
      >
        <div
          className="h-full rounded-full bg-gradient-to-r from-accent to-accent-hover"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
};

export default ProgressBar;
