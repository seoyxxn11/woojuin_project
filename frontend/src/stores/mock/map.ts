import { MOCK_UNIVERSE } from '@/stores/mock/universe';
import type { ItemType } from '@/types/item';
import type { MapCategory, MapPlace } from '@/types/map';

export const MAP_ITEM_TYPE_LABEL: Record<ItemType, string> = {
  URL: '링크',
  IMAGE: '사진',
  MEMO: '메모',
};

/**
 * 지도 API가 구현되기 전까지 우주뷰 아이템에 지도 전용 목업 위치만 합성한다.
 * item의 id/type/title/url은 MOCK_UNIVERSE를 단일 원본으로 사용한다.
 */
const LOCATION_BY_ITEM_ID: Record<number, Pick<MapPlace, 'lat' | 'lng' | 'address'>> = {
  20: { lat: 37.5796, lng: 126.977, address: '서울특별시 종로구 사직로 161' },
  21: { lat: 35.1587, lng: 129.1604, address: '부산광역시 해운대구 우동' },
  22: { lat: 37.7519, lng: 128.8761, address: '강원특별자치도 강릉시 경강로' },
  23: { lat: 35.8151, lng: 127.153, address: '전북특별자치도 전주시 완산구' },
  24: { lat: 34.7604, lng: 127.6622, address: '전라남도 여수시 중앙동' },
  25: { lat: 33.4584, lng: 126.9425, address: '제주특별자치도 서귀포시 성산읍' },
  26: { lat: 33.3938, lng: 126.2398, address: '제주특별자치도 제주시 한림읍' },
  27: { lat: 33.4623, lng: 126.9356, address: '제주특별자치도 서귀포시 성산읍' },
  28: { lat: 37.5446, lng: 127.0559, address: '서울특별시 성동구 성수이로' },
  29: { lat: 37.5467, lng: 127.0436, address: '서울특별시 성동구 서울숲길' },
  30: { lat: 37.5429, lng: 127.0522, address: '서울특별시 성동구 연무장길' },
  31: { lat: 37.5481, lng: 127.0611, address: '서울특별시 성동구 아차산로' },
  32: { lat: 37.5475, lng: 127.0418, address: '서울특별시 성동구 왕십리로' },
  33: { lat: 37.5172, lng: 127.0473, address: '서울특별시 강남구 도산대로' },
  34: { lat: 37.5662, lng: 126.983, address: '서울특별시 중구 을지로' },
  35: { lat: 37.5563, lng: 126.922, address: '서울특별시 마포구 동교로' },
  36: { lat: 37.5788, lng: 126.9707, address: '서울특별시 종로구 자하문로' },
};

const mapConstellations = MOCK_UNIVERSE.constellations.filter((constellation) =>
  constellation.items.some((item) => LOCATION_BY_ITEM_ID[item.id] !== undefined),
);

export const MAP_CATEGORIES: MapCategory[] = mapConstellations.map((constellation) => ({
  id: constellation.categoryId,
  label: constellation.categoryName.replace(/^#/, ''),
  color: `#${constellation.color.toString(16).padStart(6, '0')}`,
}));

export const MAP_PLACES: MapPlace[] = mapConstellations.flatMap((constellation) =>
  constellation.items.flatMap((item) => {
    const location = LOCATION_BY_ITEM_ID[item.id];
    if (!location) return [];

    return [
      {
        ...item,
        categoryId: constellation.categoryId,
        ...location,
      },
    ];
  }),
);
