import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { classNames } from '@/utils/classNames';

interface GlassButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: ReactNode;
  /** 주면 아이콘 옆에 라벨이 붙어 알약형이 된다. 없으면 40×38 정사각 */
  label?: string;
  /** 우상단에 겹쳐 얹는 것 — 알림 안 읽음 점 등 */
  badge?: ReactNode;
}

/**
 * 반투명 유리 버튼 — 스테이지 위에 뜨는 아이콘 버튼의 공통 껍데기.
 * 알림·공유 등 목업에서 반복되는 40×38 / border / backdrop-blur 디자인.
 *
 * 정체성(아이콘·라벨·동작)은 넘겨받고, 껍데기만 여기서 책임진다.
 * 라벨이 없으면 aria-label 을 꼭 넘겨 스크린리더가 읽을 수 있게 한다.
 */
const GlassButton = ({ icon, label, badge, className, type, ...rest }: GlassButtonProps) => (
  <button
    type={type ?? 'button'}
    className={classNames(
      'relative inline-flex h-[38px] items-center justify-center gap-[7px] rounded-md',
      'border border-border bg-sidebar/85 text-text-2 backdrop-blur-md transition-colors',
      'cursor-pointer hover:text-text-1 disabled:cursor-default disabled:opacity-40',
      '[&>svg]:h-4 [&>svg]:w-4',
      label ? 'px-3.5 text-[13px] font-semibold' : 'w-10',
      className,
    )}
    {...rest}
  >
    {icon}
    {label}
    {badge}
  </button>
);

export default GlassButton;
