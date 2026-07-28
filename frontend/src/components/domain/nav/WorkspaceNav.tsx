import { useState } from 'react';
import NavItem from '@/components/ui/nav/NavItem';
import CreateWorkspaceModal from '@/components/domain/nav/CreateWorkspaceModal';
import { PlanetIcon, WorkspacesIcon } from '@/assets/icons';
import { useSpaces } from '@/hooks/useSpaces';
import { classNames } from '@/utils/classNames';
import { useSideBar } from '@/stores/context/SideBarContext';

/** SPACE 라벨 + 워크스페이스 목록 (접기 가능) */
const WorkspaceNav = () => {
  const { sideBarClosed } = useSideBar();

  // 목록 펼침은 이 영역 안에서만 쓰이는 상태
  const [listOpen, setListOpen] = useState(true);
  const [createModalOpen, setCreateModalOpen] = useState(false);

  // 개인 스페이스는 이미 빠져 있다 — 무엇이 개인인지는 useSpaces 만 안다
  const { teams } = useSpaces();

  const handleNewWorkspace = () => {
    setCreateModalOpen(true);
  };

  return (
    <>
      {!sideBarClosed && (
        <div className="px-3.5 pt-5 pb-2 text-[11px] font-bold tracking-[0.16em] text-text-3">
          SPACE
        </div>
      )}

      <NavItem
        icon={<WorkspacesIcon />}
        label="Workspaces"
        collapsed={sideBarClosed}
        onClick={() => setListOpen((o) => !o)}
        trailing={
          !sideBarClosed && (
            <span
              className={classNames(
                'ml-auto text-[11px] transition-transform duration-200',
                !listOpen && 'rotate-180',
              )}
            >
              ⌃
            </span>
          )
        }
      />

      {listOpen && (
        /* 들여쓰기는 목록의 책임 — 컨테이너 패딩이라 자식 폭이 자동으로 좁아진다 */
        <div className={classNames(!sideBarClosed && 'pl-1')}>
          {teams.map((ws) => (
            <NavItem
              key={ws.id}
              icon={<PlanetIcon />}
              label={ws.name}
              to={`/workspace/${ws.id}`}
              collapsed={sideBarClosed}
            />
          ))}
          <NavItem
            icon={<span className="text-[17px] leading-none">＋</span>}
            label="New workspace"
            muted
            collapsed={sideBarClosed}
            onClick={handleNewWorkspace}
          />
        </div>
      )}

      <CreateWorkspaceModal open={createModalOpen} onClose={() => setCreateModalOpen(false)} />
    </>
  );
};

export default WorkspaceNav;
