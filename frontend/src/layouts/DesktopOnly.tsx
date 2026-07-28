import { Navigate, Outlet, useParams } from 'react-router-dom';
import { useIsDesktop } from '@/hooks/useIsDesktop';

/**
 * 데스크톱에서만 열리는 화면들의 가드.
 *
 * ViewBar 가 모바일에서 감춰지므로 평소엔 발동할 일이 없다. 실제로 일하는 경우는
 * 공유 링크·북마크·주소창 직접 입력, 그리고 데스크톱에서 창을 좁혔을 때다.
 *
 * 좁아지면 즉시 성좌로 돌려보낸다. replace 인 이유: push 면 뒤로가기 →
 * 다시 이 가드 → 또 리다이렉트로 뒤로가기가 영영 안 먹는다.
 */
const DesktopOnly = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const isDesktop = useIsDesktop();

  if (!isDesktop) {
    return <Navigate to={`/workspace/${workspaceId}/universe`} replace />;
  }

  return <Outlet />;
};

export default DesktopOnly;
