import black from '@/assets/spacemans/black.png';
import blue from '@/assets/spacemans/blue.png';
import crimson from '@/assets/spacemans/crimson.png';
import green from '@/assets/spacemans/green.png';
import navy from '@/assets/spacemans/navy.png';
import orange from '@/assets/spacemans/orange.png';
import pink from '@/assets/spacemans/pink.png';
import purple from '@/assets/spacemans/purple.png';
import red from '@/assets/spacemans/red.png';
import white from '@/assets/spacemans/white.png';
import yellow from '@/assets/spacemans/yellow.png';

/** 색상 → 우주인 이미지 */
const SPACEMAN_BY_COLOR = {
  red,
  orange,
  yellow,
  green,
  blue,
  navy,
  purple,
  white,
  black,
  crimson,
  pink,
} as const;

/** 선택 가능한 우주인 색상 */
export type SpacemanColor = keyof typeof SPACEMAN_BY_COLOR;

export const SPACEMAN_COLORS = Object.keys(SPACEMAN_BY_COLOR) as SpacemanColor[];

const FALLBACK: SpacemanColor = 'white';

/**
 * 색상 이름으로 우주인 이미지 경로를 얻는다.
 *
 * 서버는 대문자("WHITE"), 목업은 소문자('red')로 주므로 여기서 맞춘다.
 * 모르는 색이거나 값이 없으면 흰색으로 대체한다 (서버가 새 색을 보내도 깨지지 않게).
 */
export const getSpacemanImage = (color: string | null | undefined): string =>
  SPACEMAN_BY_COLOR[color?.toLowerCase() as SpacemanColor] ?? SPACEMAN_BY_COLOR[FALLBACK];
