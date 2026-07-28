import { describe, it, expect } from 'vitest';
import { getSpacemanImage, SPACEMAN_COLORS } from '@/utils/getSpacemanImage';

describe('getSpacemanImage', () => {
  it('색상마다 서로 다른 이미지를 반환한다', () => {
    const urls = SPACEMAN_COLORS.map(getSpacemanImage);
    expect(new Set(urls).size).toBe(SPACEMAN_COLORS.length);
  });

  it('모르는 색이면 white 로 대체한다', () => {
    // 서버가 새 색을 보내도 이미지가 깨지지 않아야 한다
    expect(getSpacemanImage('없는색')).toBe(getSpacemanImage('white'));
    expect(getSpacemanImage('')).toBe(getSpacemanImage('white'));
  });

  describe('대소문자 — 서버는 대문자로 준다', () => {
    it('대문자 색 이름도 같은 이미지를 찾는다', () => {
      // 서버 응답이 avatarColor: "WHITE" 형태다. 소문자로 맞추지 않으면
      // 전부 fallback(white) 으로 떨어져 모든 유저가 같은 아바타가 된다
      for (const color of SPACEMAN_COLORS) {
        expect(getSpacemanImage(color.toUpperCase())).toBe(getSpacemanImage(color));
      }
    });

    it('대문자 RED 는 white 가 아니다', () => {
      // 위 검사는 fallback 이 전부 같아도 통과할 수 있어 한 건을 따로 못박는다
      expect(getSpacemanImage('RED')).not.toBe(getSpacemanImage('white'));
    });
  });

  it('값이 없으면 white 로 대체한다', () => {
    // 서버가 avatarColor 를 안 보내거나 null 을 줄 수 있다
    expect(getSpacemanImage(null)).toBe(getSpacemanImage('white'));
    expect(getSpacemanImage(undefined)).toBe(getSpacemanImage('white'));
  });
});
