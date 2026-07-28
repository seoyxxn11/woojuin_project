import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { classNames } from '@/utils/classNames';

interface SubmitButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** 요청 중 — 버튼을 잠그고 pendingLabel 을 보여준다 */
  pending?: boolean;
  /** 요청 중 라벨 (예: "저장 중..."). 없으면 children 을 그대로 둔다 */
  pendingLabel?: ReactNode;
}

/**
 * 폼 제출 버튼 — 강조색 채움. 저장·생성처럼 폼을 확정하는 자리에 쓴다.
 *
 * pending 이면 자동으로 비활성화되므로 호출부는 "입력이 유효한가"만 disabled 로 넘기면 된다.
 */
const SubmitButton = ({
  pending,
  pendingLabel,
  disabled,
  children,
  className,
  ...rest
}: SubmitButtonProps) => (
  <button
    type="submit"
    disabled={pending || disabled}
    className={classNames(
      'rounded-md bg-accent px-3 py-2 text-sm font-semibold text-white',
      'hover:bg-accent-hover disabled:opacity-50',
      className,
    )}
    {...rest}
  >
    {pending && pendingLabel ? pendingLabel : children}
  </button>
);

export default SubmitButton;
