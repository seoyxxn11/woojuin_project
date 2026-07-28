import type { SVGProps } from 'react';

const base: SVGProps<SVGSVGElement> = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
};

/** 행성(토성) — Personal Space·워크스페이스 항목 */
export function PlanetIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="3.4" fill="currentColor" stroke="none" />
      <ellipse cx="12" cy="12" rx="9" ry="3.3" transform="rotate(-18 12 12)" />
    </svg>
  );
}

/** 휴지통 */
export function TrashIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M6 7l1 13h10l1-13" />
      <path d="M10 11v6M14 11v6" />
    </svg>
  );
}

/** 사람 — 마이페이지 */
export function UserIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="8" r="3.6" />
      <path d="M4.5 20c0-3.6 3.4-6 7.5-6s7.5 2.4 7.5 6" />
    </svg>
  );
}

/** 왼쪽 화살표 — 뒤로 가기 */
export function ArrowLeftIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M19 12H5" />
      <path d="m12 19-7-7 7-7" />
    </svg>
  );
}

/** 더하기 — 추가·새로 만들기 */
export function PlusIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

/** 별자리 — 뷰바 "성좌" */
export function ConstellationIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <circle cx="6" cy="7" r="1.4" />
      <circle cx="18" cy="6" r="1.4" />
      <circle cx="13" cy="13" r="1.4" />
      <circle cx="7" cy="17" r="1.4" />
      <path d="M6 7 13 13M18 6 13 13M13 13 7 17" />
    </svg>
  );
}

/** 2×2 격자 — 뷰바 "대시보드" */
export function DashboardIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}

/** 접힌 지도 — 뷰바 "지도" */
export function MapIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3z" />
      <path d="M9 3v15M15 6v15" />
    </svg>
  );
}

/** 패널 분할 — 뷰바 "한눈에 보기" */
export function OverviewIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 10h18M9 10v10" />
    </svg>
  );
}

/** 종 — 알림 버튼 */
export function BellIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M18 9a6 6 0 1 0-12 0c0 5-2 6-2 6h16s-2-1-2-6" />
      <path d="M10.3 19a2 2 0 0 0 3.4 0" />
    </svg>
  );
}

/** 큐브 — Workspaces 그룹 헤더 */
export function WorkspacesIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="m3 8 9-5 9 5-9 5z" />
      <path d="m3 8 9 5 9-5M3 8v8l9 5 9-5V8" />
    </svg>
  );
}
