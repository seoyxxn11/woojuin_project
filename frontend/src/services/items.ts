import { api, type ApiResponse } from './client';
import type {
  ItemCreateResponse,
  ItemDetail,
  ItemListResponse,
  ItemSearchResponse,
  ItemAiSearchResponse,
} from '@/types/item';
import type { MapPlace } from '@/types/map';

// ── 검색 ────────────────────────────────────────
// 일반(키워드)과 AI(자연어)를 경로로 나눈다 — 응답 content 는 동일해 카드 재사용.
export async function searchItems(workspaceId: number, q: string, page: number, size: number) {
  const params = new URLSearchParams({ q, page: String(page), size: String(size) });
  const res = await api.get<ApiResponse<ItemSearchResponse>>(
    `/workspaces/${workspaceId}/search?${params}`,
  );
  return res.data.data;
}

export async function aiSearchItems(workspaceId: number, q: string, page: number, size: number) {
  const params = new URLSearchParams({ q, page: String(page), size: String(size) });
  const res = await api.get<ApiResponse<ItemAiSearchResponse>>(
    `/workspaces/${workspaceId}/ai/search?${params}`,
  );
  return res.data.data;
}

// ── 휴지통 ───────────────────────────────────────
// 목록은 일반 목록과 같은 content(카드 재사용). 복구/영구삭제는 아이템 단위.
export async function fetchTrash(workspaceId: number, page: number, size: number) {
  const res = await api.get<ApiResponse<ItemListResponse>>(
    `/workspaces/${workspaceId}/trash?page=${page}&size=${size}`,
  );
  return res.data.data;
}

// 복구 — 원래 카테고리로 되돌아간다
export async function restoreItem(itemId: number) {
  await api.post<ApiResponse<ItemDetail>>(`/items/${itemId}/restore`);
}

// 영구 삭제 — 되돌릴 수 없다
export async function deleteItemPermanently(itemId: number) {
  await api.delete<ApiResponse<null>>(`/items/${itemId}/permanent`);
}

//워크스페이스 아이템 받아오기
//필터는 전부 서버가 처리한다(즐겨찾기·카테고리·정렬) — queryKey 로 캐싱/재요청을 태운다.
export interface ItemFilters {
  /** 켜졌을 때만 보낸다(끄면 전체). false 는 파라미터를 생략 = 전체 */
  favorite?: boolean;
  /** 카테고리 다중 OR 필터 — ?categoryIds=1&categoryIds=2. 빈 배열이면 전체 */
  categoryIds?: number[];
  /** 정렬 키(기본 latest). 서버 기본값과 같아 없으면 생략 */
  sort?: string;
}

export interface workspaceProps extends ItemFilters {
  size: number;
  page?: number;
  workspaceId: number;
}

export async function fetchItems({
  size,
  page,
  workspaceId,
  favorite,
  categoryIds,
  sort,
}: workspaceProps) {
  // 값이 있을 때만 붙인다 — 빈 필터는 아예 보내지 않아 "전체" 가 된다
  const params = new URLSearchParams();
  params.set('page', String(page ?? 0));
  params.set('size', String(size));
  if (favorite) params.set('favorite', 'true');
  if (sort) params.set('sort', sort);
  categoryIds?.forEach((id) => params.append('categoryIds', String(id)));

  const res = await api.get<ApiResponse<ItemListResponse>>(
    `/workspaces/${workspaceId}/items?${params.toString()}`,
  );
  return res.data.data;
}

// 아이템 상세 — 목록엔 없는 본문(content)·원본 이미지(imageUrl)를 받는다.
// GET /items/{itemId} → ItemDetailResponse (아이템 id 는 전역 유일이라 워크스페이스 스코프가 없다)
export async function fetchItem(itemId: number) {
  const res = await api.get<ApiResponse<ItemDetail>>(`/items/${itemId}`);
  return res.data.data;
}

export async function fetchMapPlaces(workspaceId: number) {
  const res = await api.get<ApiResponse<MapPlace[]>>(`/workspaces/${workspaceId}/items/geo`);
  return res.data.data;
}

/** 부분 수정 — null/undefined 필드는 안 바꾼다. 제목·본문·카테고리는 이 하나로. */
export interface ItemPatch {
  title?: string;
  content?: string;
  /** 이 아이템의 카테고리 전체 집합(추가·삭제 모두 새 집합을 통째로 보낸다) */
  categoryIds?: number[];
}

// PATCH /items/{itemId} → 갱신된 상세
export async function updateItem(itemId: number, patch: ItemPatch) {
  const res = await api.patch<ApiResponse<ItemDetail>>(`/items/${itemId}`, patch);
  return res.data.data;
}

/** 즐겨찾기 응답 — 바뀐 상태만 얇게 온다({ itemId, favorite }) */
export interface FavoriteResponse {
  itemId: number;
  favorite: boolean;
}

// 즐겨찾기 — 전용 엔드포인트. 바디 없음. POST 로 등록, DELETE 로 해제.
// 응답의 favorite 로 캐시를 바로 갈아끼워 재요청 없이 반영한다.
export async function addFavorite(itemId: number) {
  const res = await api.post<ApiResponse<FavoriteResponse>>(`/items/${itemId}/favorite`);
  return res.data.data;
}
export async function removeFavorite(itemId: number) {
  const res = await api.delete<ApiResponse<FavoriteResponse>>(`/items/${itemId}/favorite`);
  return res.data.data;
}

// DELETE /items/{itemId} → 휴지통으로 이동(soft delete)
export async function deleteItem(itemId: number) {
  await api.delete(`/items/${itemId}`);
}

/**
 * title 은 공유 시트가 준 제목(FR-013). 쿠팡처럼 봇을 막는 쇼핑몰은 서버가 제목을
 * 크롤링할 수 없어서, 공유 텍스트에서 건진 상품명을 함께 보낸다. 서버는 크롤링이
 * 실패했을 때만 이 값을 쓰는 게 아니라 크롤링 제목보다 우선해서 쓴다 — 자세한 건
 * 백엔드 Item.applyPreview javadoc 참고. 직접 URL 을 입력해 저장할 땐 넘기지 않는다.
 */
export async function saveUrl(workspaceId: number, url: string, title?: string | null) {
  // 즉시 200 응답 (status: PROCESSING) — "저장은 1초" (NFR-001)
  const res = await api.post<ApiResponse<ItemCreateResponse>>(`/workspaces/${workspaceId}/items`, {
    type: 'URL',
    url,
    // 없을 때 키를 아예 빼는 이유: 빈 문자열을 보내면 서버가 blank 를 null 로 눕히긴
    // 하지만, 애초에 안 보내는 쪽이 의도가 분명하다
    ...(title ? { title } : {}),
  });
  return res.data.data;
}

export async function saveMemo(workspaceId: number, content: string) {
  // 즉시 200 응답 (status: PROCESSING) — "저장은 1초" (NFR-001)
  const res = await api.post<ApiResponse<ItemCreateResponse>>(`/workspaces/${workspaceId}/items`, {
    type: 'MEMO',
    content: content,
  });
  return res.data.data;
}

export async function saveImage(workspaceId: number, file: File) {
  // 이미지만 multipart/form-data 다. 일반 객체로 넘기면 axios 가 JSON 으로 보내 400 이 난다.
  // Content-Type 은 직접 지정하지 않는다 — boundary 가 빠져서 파싱이 깨진다 (브라우저가 붙여준다).
  const formData = new FormData();
  formData.append('file', file);

  // 즉시 200 응답 (status: PROCESSING) — "저장은 1초" (NFR-001)
  const res = await api.post<ApiResponse<ItemCreateResponse>>(
    `/workspaces/${workspaceId}/items`,
    formData,
  );
  return res.data.data;
}
