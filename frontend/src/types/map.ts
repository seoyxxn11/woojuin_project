import type { ItemType } from '@/types/item';

export type MapCategoryId = number;

export interface MapCategory {
  id: MapCategoryId;
  label: string;
  color: string;
}

export interface MapPlace {
  id: number;
  categoryId: MapCategoryId;
  type: ItemType;
  position: [number, number, number];
  title: string;
  url?: string;
  lat: number;
  lng: number;
  address: string;
}
