import { useState } from 'react';
import { classNames } from '@/utils/classNames';
import { SideBarProvider } from '@/stores/context/SideBarContext';
import SideBarBrand from './SideBarBrand';
import FixedNav from './FixedNav';
import WorkspaceNav from './WorkspaceNav';
import StorageBar from './StorageBar';
import SideBarUser from './SideBarUser';

const SideBar = () => {
  const [sideBarClosed, setSideBarClosed] = useState(false);

  const toggleSideBar = () => setSideBarClosed((closed) => !closed);

  return (
    <SideBarProvider value={{ sideBarClosed, toggleSideBar }}>
      <aside
        className={classNames(
          // 모바일(< breakpoint-desktop)에서는 하단 탭바가 대신하므로 감춘다
          'hidden desktop:flex flex-col shrink-0 h-dvh z-20 transition-[width] duration-200 overflow-y-scroll scrollbar-none',
          'bg-sidebar border-r border-border-soft pt-[18px] pb-3.5',
          sideBarClosed ? 'w-sidebar-collapsed px-2.5' : 'w-sidebar px-3.5',
        )}
      >
        <SideBarBrand />
        <FixedNav />
        <WorkspaceNav />
        <div className="flex-1" />
        <StorageBar />
        <SideBarUser />
      </aside>
    </SideBarProvider>
  );
};

export default SideBar;
