import ProgressBar from '@/components/ui/ProgressBar';
import { useUser } from '@/hooks/useUser';
import { useSideBar } from '@/stores/context/SideBarContext';

/** 저장 공간 사용량 — 접힘 상태에서는 표시하지 않는다 */
const StorageBar = () => {
  const { sideBarClosed } = useSideBar();

  // 서버 상태
  const { remainMemories, fullMemories } = useUser();

  if (sideBarClosed) return null;

  return (
    <div className="px-2.5 py-3">
      <ProgressBar label="저장 공간" value={remainMemories} max={fullMemories} unit="GB" />
    </div>
  );
};

export default StorageBar;
