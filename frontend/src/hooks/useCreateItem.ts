import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import type { ItemCreateResponse } from '@/types/item';

/**
 * 저장 항목 생성 공통부 — 링크·사진·메모 폼이 공유한다.
 *
 * 타입마다 요청 형식이 달라(URL·MEMO 는 JSON, IMAGE 는 multipart) 저장 함수만 주입받고,
 * 워크스페이스 id·목록 갱신·에러 메시지·닫기는 여기서 한 번만 처리한다.
 *
 * 서버는 PROCESSING 을 바로 준다 — 분석이 끝나길 기다리지 않고 닫는다 (NFR-001).
 */
export function useCreateItem<TInput>(
  save: (workspaceId: number, input: TInput) => Promise<ItemCreateResponse>,
  onDone: () => void,
) {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const queryClient = useQueryClient();
  const id = Number(workspaceId);

  const mutation = useMutation({
    mutationFn: (input: TInput) => save(id, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['items', id] });
      onDone();
    },
  });

  const errorMessage = axios.isAxiosError(mutation.error)
    ? (mutation.error.response?.data?.message ?? '저장에 실패했습니다')
    : null;

  return { save: mutation.mutate, isPending: mutation.isPending, errorMessage };
}
