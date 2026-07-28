import { useQuery } from '@tanstack/react-query';
import { fetchMyWorkspaces } from '@/services/workspaces';

/** 내가 속한 워크스페이스 목록 — 사이드바 등에서 쓰는 서버 상태 진입점 */
export function useWorkspaces() {
  return useQuery({
    queryKey: ['workspaces'],
    queryFn: fetchMyWorkspaces,
  });
}
