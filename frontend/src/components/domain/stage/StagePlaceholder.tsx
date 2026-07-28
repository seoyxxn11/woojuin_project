interface StagePlaceholderProps {
  /** 이 자리에 들어올 화면 이름 */
  label: string;
}

/**
 * 아직 만들지 않은 스테이지 뷰의 자리 표시.
 *
 * 뷰바로 옮겨왔을 때 "빈 화면"과 "터진 화면"을 구분하려고 둔다.
 * 실제 화면을 만들면 그대로 지운다.
 */
const StagePlaceholder = ({ label }: StagePlaceholderProps) => (
  <div className="grid h-full w-full place-items-center bg-space">
    <p className="text-sm text-text-3">{label} — 준비 중</p>
  </div>
);

export default StagePlaceholder;
