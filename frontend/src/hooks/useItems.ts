import { useQuery } from '@tanstack/react-query';
import { fetchItems } from '@/services/items';

/** 특정 워크스페이스에 저장된 아이템 목록 — 서버 상태 진입점 */
export function useItems(workspaceId: number) {
  return useQuery({
    queryKey: ['items', workspaceId],
    queryFn: () => fetchItems(workspaceId),
  });
}
