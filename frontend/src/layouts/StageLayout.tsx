import { Outlet, useParams } from 'react-router-dom';
import { useAtomValue } from 'jotai';
import StageHeader from '@/components/domain/stage/StageHeader';
import AddBtn from '@/components/domain/header/AddBtn';
import { useWorkspaces } from '@/hooks/useWorkspaces';
import { stageMetaAtom } from '@/stores/stageAtoms';

/**
 * 스테이지 셸 — 성좌·대시보드·지도·한눈에 보기가 공유하는 상단 헤더.
 *
 * 네 뷰는 같은 워크스페이스를 다르게 보여줄 뿐이라 제목과 뷰바가 동일하다.
 * 헤더를 페이지마다 두면 뷰를 옮길 때마다 제목이 사라졌다 다시 그려지므로
 * 라우트 레벨에 한 번만 둔다.
 *
 * <Outlet /> 을 먼저 두는 건 헤더(absolute)가 항상 위에 오게 하기 위함이다.
 */
const StageLayout = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const { data: workspaces } = useWorkspaces();
  const meta = useAtomValue(stageMetaAtom);

  // 제목은 URL 이 가리키는 워크스페이스의 이름. 목록이 오기 전엔 빈 제목 대신 폴백을 쓴다
  const current = workspaces?.find((workspace) => workspace.id === Number(workspaceId));

  return (
    <div className="relative h-full w-full">
      <Outlet />
      <StageHeader title={current?.name ?? 'My Universe'} meta={meta} actions={<AddBtn />} />
    </div>
  );
};

export default StageLayout;
