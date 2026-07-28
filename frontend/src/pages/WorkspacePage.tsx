import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { useItems } from '@/hooks/useItems';
import { useWorkspaces } from '@/hooks/useWorkspaces';
import { saveUrl } from '@/services/items';

const STATUS_LABEL: Record<string, string> = {
  PROCESSING: '처리 중',
  DONE: '완료',
  PARTIAL: '일부 완료',
  FAILED: '실패',
};

/** 워크스페이스별 URL 저장 + 저장 항목 목록 */
export default function WorkspacePage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const id = Number(workspaceId);
  const queryClient = useQueryClient();
  const [url, setUrl] = useState('');

  const { data: workspaces } = useWorkspaces();
  const { data: items, isLoading } = useItems(id);
  const workspaceName = workspaces?.find((ws) => ws.id === id)?.name;

  const saveMutation = useMutation({
    mutationFn: (value: string) => saveUrl(id, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['items', id] });
      setUrl('');
    },
  });

  const errorMessage = axios.isAxiosError(saveMutation.error)
    ? (saveMutation.error.response?.data?.message ?? 'URL 저장에 실패했습니다')
    : null;

  return (
    <div className="h-full overflow-y-auto p-8">
      <h1 className="text-display font-extrabold text-text-1">{workspaceName ?? '워크스페이스'}</h1>

      <form
        className="mt-6 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (url.trim()) saveMutation.mutate(url.trim());
        }}
      >
        <input
          type="url"
          placeholder="저장할 URL을 붙여넣으세요"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="flex-1 rounded-md border border-border bg-surface-2 px-3 py-2 text-text-1 outline-none focus:border-accent"
          required
        />
        <button
          type="submit"
          disabled={saveMutation.isPending}
          className="rounded-md bg-accent px-4 py-2 font-semibold text-white hover:bg-accent-hover disabled:opacity-50"
        >
          {saveMutation.isPending ? '저장 중...' : '저장'}
        </button>
      </form>
      {errorMessage && <p className="mt-2 text-sm text-red-500">{errorMessage}</p>}

      <ul className="mt-8 flex flex-col gap-2">
        {isLoading && <li className="text-text-3">불러오는 중...</li>}
        {!isLoading && items?.content.length === 0 && (
          <li className="text-text-3">아직 저장된 항목이 없습니다.</li>
        )}
        {items?.content.map((item) => (
          <li
            key={item.itemId}
            className="rounded-md border border-border bg-surface-2 px-3.5 py-3"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate font-semibold text-text-1">
                {item.title ?? item.url ?? `아이템 #${item.itemId}`}
              </span>
              <span className="shrink-0 text-xs text-text-3">{STATUS_LABEL[item.status]}</span>
            </div>
            {item.url && <div className="mt-1 truncate text-xs text-text-3">{item.url}</div>}
          </li>
        ))}
      </ul>
    </div>
  );
}
