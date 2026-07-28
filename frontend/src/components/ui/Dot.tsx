import { classNames } from '@/utils/classNames';

/** 지름 — 목업이 쓰는 6·7·8px */
const SIZE = {
  sm: 'w-1.5 h-1.5', // 6px — 태그·툴팁 안
  md: 'w-[7px] h-[7px]', // 7px — 사이드바 라이브 점
  lg: 'w-2 h-2', // 8px — 컨텍스트 메뉴·검색 결과
} as const;

/**
 * 색은 text-* 로 지정하고 bg-current 로 받는다.
 * 글로우(box-shadow)도 currentColor 를 쓰므로 색이 한 곳에서만 정해진다.
 */
const COLOR = {
  accent: 'text-accent',
  lavender: 'text-star-lavender',
  blue: 'text-star-blue',
  green: 'text-star-green',
  orange: 'text-star-orange',
  yellow: 'text-star-yellow',
  white: 'text-star-white',
} as const;

export type DotSize = keyof typeof SIZE;
export type DotColor = keyof typeof COLOR;

interface DotProps {
  size?: DotSize;
  color?: DotColor;
  /** 은은한 발광. 디자인 시스템 규칙상 3~5px 를 넘기지 않는다 */
  glow?: boolean;
  /** 배치용 (ml-auto, absolute right-3 …) */
  className?: string;
}

/** 상태·카테고리를 나타내는 색 점 */
const Dot = ({ size = 'md', color = 'accent', glow = false, className }: DotProps) => (
  <span
    aria-hidden="true"
    className={classNames(
      'inline-block shrink-0 rounded-full bg-current',
      SIZE[size],
      COLOR[color],
      glow && 'shadow-[0_0_3px_currentColor]',
      className,
    )}
  />
);

export default Dot;
