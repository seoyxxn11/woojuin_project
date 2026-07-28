import { useState } from 'react';
import { useSetAtom } from 'jotai';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useUser } from '@/hooks/useUser';
import { classNames } from '@/utils/classNames';
import { getSpacemanImage } from '@/utils/getSpacemanImage';
import { useSideBar } from '@/stores/context/SideBarContext';
import { logout } from '@/services/auth';
import { accessTokenAtom, refreshTokenAtom } from '@/stores/authAtoms';

/** 하단 유저 푸터 — 접힘 상태에서는 아바타만 남는다 */
const SideBarUser = () => {
  const { sideBarClosed } = useSideBar();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const setAccessToken = useSetAtom(accessTokenAtom);
  const setRefreshToken = useSetAtom(refreshTokenAtom);
  const [menuOpen, setMenuOpen] = useState(false);

  // 서버 상태
  const { nickName, email, avatarColor } = useUser();

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // 서버 호출이 실패해도(네트워크 오류 등) 로컬 로그아웃은 진행한다
    }
    setAccessToken(null);
    setRefreshToken(null);
    queryClient.clear();
    navigate('/');
  };

  return (
    <section
      className={classNames(
        'relative flex items-center gap-[11px] border-t border-border-soft py-3',
        sideBarClosed ? 'justify-center' : 'px-2.5',
      )}
    >
      <div className="w-9 h-9 rounded-full bg-surface-3 shrink-0 overflow-hidden">
        <img
          src={getSpacemanImage(avatarColor)}
          alt={`${nickName} 프로필`}
          className="w-full h-full object-cover block"
        />
      </div>
      {!sideBarClosed && (
        <>
          <div className="min-w-0">
            <div className="text-sm font-bold text-text-1 truncate">{nickName}</div>
            <div className="text-xs text-text-3 truncate">{email}</div>
          </div>
          <button
            type="button"
            aria-label="계정 메뉴"
            onClick={() => setMenuOpen((open) => !open)}
            className="ml-auto text-text-3 hover:text-text-1 cursor-pointer"
          >
            ···
          </button>
          {menuOpen && (
            <>
              {/* 바깥 클릭으로 닫기 — 메뉴보다 낮은 z로 전체 화면을 덮는다 */}
              <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
              <div className="absolute bottom-full right-2.5 z-50 mb-2 min-w-[120px] overflow-hidden rounded-md border border-border bg-surface-2 shadow-float">
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full px-3 py-2 text-left text-sm text-text-1 hover:bg-surface-3"
                >
                  로그아웃
                </button>
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
};

export default SideBarUser;
