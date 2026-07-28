import { Outlet } from 'react-router-dom';
import SideBar from '@/components/domain/nav/SideBar';
import TabBar from '@/components/domain/nav/TabBar';

/**
 * 앱 공통 셸 — 내비게이션이 폭에 따라 교체된다 (경계는 theme.css 의 --breakpoint-desktop).
 *
 *   < desktop  하단 탭바 (캔버스 위에 떠 있다)
 *   >= desktop 좌측 사이드바 (접힘 지원)
 *
 * 페이지는 한 벌이고 셸만 갈린다. 교체는 CSS 로만 해서 창 폭을 바꾸면 즉시 따라온다.
 * h-dvh 인 이유: 모바일 주소창이 접혔다 펴질 때 100vh 는 화면 밖으로 넘친다.
 */
const Layout = () => {
  return (
    <div className="flex h-dvh overflow-hidden">
      <SideBar />

      <div className="relative flex min-w-0 flex-1 flex-col">
        <main className="relative flex-1 overflow-hidden bg-space">
          <Outlet />
        </main>

        {/* 노출 분기는 TabBar 가 스스로 한다 — 여기서는 위치만 정한다 */}
        <TabBar className="absolute inset-x-0 bottom-0 z-30" />
      </div>
    </div>
  );
};

export default Layout;
