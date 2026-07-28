/**
 * 성좌 뷰 데이터 — **서버 응답 형태**.
 *
 * 서버는 카테고리별로 묶인 아이템(별)과 그 3D 좌표를 준다.
 * 카테고리 자체의 위치·크기는 서버가 주지 않고 클라이언트가 계산한다(deriveHubs).
 *
 * TODO: MOCK_UNIVERSE 를 `GET /workspaces/{id}/universe` 응답으로 교체
 */

export type Vec3 = [number, number, number];

/** 저장물 종류 — 백엔드 ItemType enum 과 동일하게 유지할 것 */
export type ItemType = 'URL' | 'IMAGE' | 'MEMO';

export const TYPE_LABEL: Record<ItemType, string> = {
  URL: '링크',
  IMAGE: '사진',
  MEMO: '메모',
};

/** 미분류 별 — 어느 별자리에도 속하지 않는다 */
export const UNCLASSIFIED_COLOR = 0xf5f1e8;

/* ── 별 ─────────────────────────────────────────────── */

/**
 * 아이템 별은 크기를 갖지 않는다 — 전부 같은 기본 크기로 그린다(STAR_RADIUS).
 * 크기가 의미를 갖는 건 별자리뿐이고, 그건 아이템 개수에서 파생한다.
 */
export interface Star {
  id: number;
  /** 아이템 자신의 3D 좌표 */
  position: Vec3;
  title: string;
  type: ItemType;
  /** URL 타입일 때만 채워진다 — 있으면 클릭 시 바로 이동, 없으면 상세 조회 */
  url?: string;
}

/** 아이템 별 기본 크기 */
export const STAR_RADIUS = 0.6;

/* ── 별자리 ─────────────────────────────────────────── */

export interface Constellation {
  categoryId: number;
  categoryName: string;
  /** 별자리 색 (16진). 예: 0xf2d96b — 서버가 배정한다 */
  color: number;
  /** 개수는 items.length 로 판단한다 (별도 카운트 필드를 두지 않음) */
  items: Star[];
}

export interface UniverseResponse {
  constellations: Constellation[];
  /** 아직 분류되지 않은 별 — 연결선 없이 홀로 뜬다 */
  unclassified: Star[];
}

/* ── 목업 데이터 ─────────────────────────────────────
   서버 연동 전까지 쓰는 고정 데이터.
   TODO: GET /workspaces/{id}/universe 응답으로 교체 */

export const MOCK_UNIVERSE: UniverseResponse = {
  constellations: [
    {
      categoryId: 1,
      categoryName: '#Ideas',
      color: 0xc9b8ff,
      items: [
        {
          id: 1,
          type: 'URL',
          position: [-8, 18.5, 5],
          title: '크롬 익스텐션 저장',
          url: 'https://example.com',
        },
        { id: 2, type: 'IMAGE', position: [-11.32, 15, 8.04], title: '인스타 공유 링크' },
        { id: 3, type: 'MEMO', position: [-8, 9.5, 5], title: '카톡 나에게 보내기' },
      ],
    },
    {
      categoryId: 2,
      categoryName: '#Architecture',
      color: 0x8fb4ff,
      items: [
        { id: 4, type: 'IMAGE', position: [7, 20.5, -3], title: '카톡 나에게 보내기' },
        { id: 5, type: 'MEMO', position: [3.87, 18.5, -0.13], title: 'OG 미리보기' },
        {
          id: 6,
          type: 'URL',
          position: [7.45, 15.17, -8.17],
          title: 'OCR 텍스트',
          url: 'https://example.com',
        },
        { id: 7, type: 'IMAGE', position: [7, 13.5, -3], title: '카카오맵 좌표' },
      ],
    },
    {
      categoryId: 3,
      categoryName: '#OperatingSystem',
      color: 0x8fb4ff,
      items: [
        { id: 8, type: 'MEMO', position: [18, 12.5, -7], title: 'OCR 텍스트' },
        {
          id: 9,
          type: 'URL',
          position: [15.13, 11.25, -4.37],
          title: '카카오맵 좌표',
          url: 'https://example.com',
        },
        { id: 10, type: 'IMAGE', position: [18.48, 9, -12.48], title: 'oEmbed 카드' },
        { id: 11, type: 'MEMO', position: [19.84, 7.25, -4.59], title: '요약본 v2' },
        {
          id: 12,
          type: 'URL',
          position: [18, 4.5, -7],
          title: '크롬 익스텐션 저장',
          url: 'https://example.com',
        },
      ],
    },
    {
      categoryId: 4,
      categoryName: '#SpringBoot',
      color: 0x8fb4ff,
      items: [
        {
          id: 13,
          type: 'URL',
          position: [13, 6.5, 3],
          title: 'oEmbed 카드',
          url: 'https://example.com',
        },
        { id: 14, type: 'IMAGE', position: [9.68, 3, 6.04], title: '요약본 v2' },
        { id: 15, type: 'MEMO', position: [13, -2.5, 3], title: '크롬 익스텐션 저장' },
      ],
    },
    {
      categoryId: 5,
      categoryName: '#Backend',
      color: 0x8fb4ff,
      items: [
        { id: 16, type: 'IMAGE', position: [4, 1.5, 7], title: '크롬 익스텐션 저장' },
        { id: 17, type: 'MEMO', position: [0.87, -0.5, 9.87], title: '인스타 공유 링크' },
        {
          id: 18,
          type: 'URL',
          position: [4.45, -3.83, 1.83],
          title: '카톡 나에게 보내기',
          url: 'https://example.com',
        },
        { id: 19, type: 'IMAGE', position: [4, -5.5, 7], title: 'OG 미리보기' },
      ],
    },
    {
      categoryId: 6,
      categoryName: '#Travel',
      color: 0xb8e6a3,
      items: [
        { id: 20, type: 'MEMO', position: [13, -0.5, -5], title: '카톡 나에게 보내기' },
        {
          id: 21,
          type: 'URL',
          position: [10.13, -1.75, -2.37],
          title: 'OG 미리보기',
          url: 'https://example.com',
        },
        { id: 22, type: 'IMAGE', position: [13.48, -4, -10.48], title: 'OCR 텍스트' },
        { id: 23, type: 'MEMO', position: [14.84, -5.75, -2.59], title: '카카오맵 좌표' },
        {
          id: 24,
          type: 'URL',
          position: [13, -8.5, -5],
          title: 'oEmbed 카드',
          url: 'https://example.com',
        },
      ],
    },
    {
      categoryId: 7,
      categoryName: '#Jeju',
      color: 0xb8e6a3,
      items: [
        {
          id: 25,
          type: 'URL',
          position: [9, -7.5, 3],
          title: 'OCR 텍스트',
          url: 'https://example.com',
        },
        { id: 26, type: 'IMAGE', position: [5.68, -11, 6.04], title: '카카오맵 좌표' },
        { id: 27, type: 'MEMO', position: [9, -16.5, 3], title: 'oEmbed 카드' },
      ],
    },
    {
      categoryId: 8,
      categoryName: '#Seongsu',
      color: 0xf5b08a,
      items: [
        { id: 28, type: 'IMAGE', position: [-19, -4.5, -2], title: 'oEmbed 카드' },
        { id: 29, type: 'MEMO', position: [-22.13, -6.5, 0.87], title: '요약본 v2' },
        {
          id: 30,
          type: 'URL',
          position: [-18.55, -9.83, -7.17],
          title: '크롬 익스텐션 저장',
          url: 'https://example.com',
        },
        { id: 31, type: 'IMAGE', position: [-19, -11.5, -2], title: '인스타 공유 링크' },
      ],
    },
    {
      categoryId: 9,
      categoryName: '#Coffee',
      color: 0xf2d96b,
      items: [
        { id: 32, type: 'MEMO', position: [-5, -13.5, 5], title: '크롬 익스텐션 저장' },
        {
          id: 33,
          type: 'URL',
          position: [-7.87, -14.75, 7.63],
          title: '인스타 공유 링크',
          url: 'https://example.com',
        },
        { id: 34, type: 'IMAGE', position: [-4.52, -17, -0.48], title: '카톡 나에게 보내기' },
        { id: 35, type: 'MEMO', position: [-3.16, -18.75, 7.41], title: 'OG 미리보기' },
        {
          id: 36,
          type: 'URL',
          position: [-5, -21.5, 5],
          title: 'OCR 텍스트',
          url: 'https://example.com',
        },
      ],
    },
    {
      categoryId: 10,
      categoryName: '#Study',
      color: 0xc9b8ff,
      items: [
        {
          id: 37,
          type: 'URL',
          position: [6, -12.5, -2],
          title: '카톡 나에게 보내기',
          url: 'https://example.com',
        },
        { id: 38, type: 'IMAGE', position: [2.68, -16, 1.04], title: 'OG 미리보기' },
        { id: 39, type: 'MEMO', position: [6, -21.5, -2], title: 'OCR 텍스트' },
      ],
    },
  ],

  unclassified: [
    {
      id: 40,
      type: 'URL',
      position: [0, 26, 0],
      title: '아직 분류되지 않은 저장물',
      url: 'https://example.com',
    },
    { id: 41, type: 'IMAGE', position: [-15.34, 15.6, 14.05], title: '아직 분류되지 않은 저장물' },
    { id: 42, type: 'MEMO', position: [2.23, 5.2, -25.38], title: '아직 분류되지 않은 저장물' },
    {
      id: 43,
      type: 'URL',
      position: [15.5, -5.2, 20.22],
      title: '아직 분류되지 않은 저장물',
      url: 'https://example.com',
    },
    { id: 44, type: 'IMAGE', position: [-20.48, -15.6, -3.62], title: '아직 분류되지 않은 저장물' },
    { id: 45, type: 'MEMO', position: [0, -26, 0], title: '아직 분류되지 않은 저장물' },
  ],
};
