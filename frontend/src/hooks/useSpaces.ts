import { useUser } from '@/hooks/useUser';
import { useWorkspaces } from '@/hooks/useWorkspaces';

/**
 * 사이드바가 쓰는 워크스페이스 분할 — "무엇이 개인 스페이스인가" 를 정하는 유일한 곳.
 *
 * FixedNav 는 개인을 그리고 WorkspaceNav 는 같은 것을 빼야 하는데,
 * 두 파일이 각자 판단하면 규칙이 어긋나는 순간 사이드바에 같은 워크스페이스가
 * 두 번 뜨거나 아예 사라진다. 그것도 조용히. 그래서 판단을 여기로 모은다.
 *
 * 개인 워크스페이스 id 는 목록이 아니라 프로필에서 온다(useUser) —
 * 목록이 아직 안 왔어도 personalSpaceId 는 알 수 있다.
 */
export function useSpaces() {
  const { personalSpaceId } = useUser();
  const { data: workspaces = [] } = useWorkspaces();

  return {
    personalSpaceId,
    /** 개인을 뺀 나머지 — 사이드바 Workspaces 목록에 들어간다 */
    teams: workspaces.filter((workspace) => workspace.id !== personalSpaceId),
  };
}
