import type { ComponentType, SVGProps } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { classNames } from '@/utils/classNames';
import { ConstellationIcon, DashboardIcon, MapIcon, OverviewIcon } from '@/assets/icons';

interface View {
  label: string;
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
  /** 워크스페이스 아래 경로 조각 */
  segment: string;
}

/** 같은 저장물을 다른 방식으로 보여주는 화면들 사이의 전환 */
const VIEWS: View[] = [
  { label: '성좌', Icon: ConstellationIcon, segment: 'universe' },
  { label: '대시보드', Icon: DashboardIcon, segment: 'library' },
  { label: '지도', Icon: MapIcon, segment: 'map' },
  { label: '한눈에 보기', Icon: OverviewIcon, segment: 'canvas' },
];

/**
 * 뷰바.
 *
 * 상대 경로(`to="library"`)를 쓰면 현재 라우트가 /workspace/12/universe 라서
 * /workspace/12/universe/library 로 붙어버린다. 그래서 절대 경로로 만든다.
 */
const ViewBar = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const { pathname } = useLocation();

  return (
    <nav
      aria-label="보기 방식"
      // 모바일에서는 하단 탭바가 뷰 전환을 대신하므로 중복이다
      className="hidden desktop:flex gap-[3px] rounded-[11px] border border-border bg-sidebar/60 p-1 backdrop-blur-md"
    >
      {VIEWS.map(({ label, Icon, segment }) => {
        const to = `/workspace/${workspaceId}/${segment}`;
        // 하위 경로(library/:catId)에서도 대시보드가 켜져 보이게 prefix 로 판단
        const active = pathname === to || pathname.startsWith(`${to}/`);

        return (
          <Link
            key={segment}
            to={to}
            title={label}
            aria-current={active ? 'page' : undefined}
            className={classNames(
              'grid h-[30px] w-[34px] cursor-pointer place-items-center rounded-sm transition-colors [&>svg]:h-4 [&>svg]:w-4',
              active ? 'bg-surface-3 text-text-1' : 'text-text-3 hover:text-text-1',
            )}
          >
            <Icon />
          </Link>
        );
      })}
    </nav>
  );
};

export default ViewBar;
