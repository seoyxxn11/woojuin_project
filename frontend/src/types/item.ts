/** 저장 항목 처리 상태 (FR-025) */
export type ItemStatus = 'PROCESSING' | 'DONE' | 'PARTIAL' | 'FAILED';

/** 저장 항목 유형 */
export type ItemType = 'URL' | 'IMAGE' | 'MEMO';

export interface ItemPreview {
  thumbnailUrl: string | null;
  description: string | null;
}

export interface Item {
  itemId: number;
  type: ItemType;
  status: ItemStatus;
  title: string | null;
  url: string | null;
  content: string | null;
  s3Key: string | null;
  preview: ItemPreview;
  favorite: boolean;
  createdAt: string;
  deletedAt: string | null;
}

export interface ItemListResponse {
  content: Item[];
  page: number;
  size: number;
  totalElements: number;
}

export interface ItemCreateResponse {
  itemId: number;
  status: ItemStatus;
  createdAt: string;
}
