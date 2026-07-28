import { describe, it, expect } from 'vitest';
import { page } from 'vitest/browser';
import { getMobileSize, getDesktopQuery } from '@/constants/breakpoints';

/**
 * 분기점의 원본은 theme.css 의 `--breakpoint-desktop` 하나다.
 * JS 가 그 값을 읽고, `desktop:` 프리픽스도 같은 값을 쓴다 — 둘이 어긋날 수 없어야 한다.
 */
describe('모바일 분기점', () => {
  it('theme.css 의 --breakpoint-desktop 을 읽는다', () => {
    const declared = getComputedStyle(document.documentElement).getPropertyValue(
      '--breakpoint-desktop',
    );

    // 변수가 실제로 존재해야 한다 — 없으면 폴백이 조용히 쓰인다
    expect(declared.trim()).not.toBe('');
    expect(getMobileSize()).toBe(Number.parseFloat(declared));
  });

  it('getDesktopQuery 는 그 값을 경계로 삼는다', () => {
    expect(getDesktopQuery()).toBe(`(min-width: ${getMobileSize()}px)`);
  });

  describe('Tailwind desktop 프리픽스와 같은 경계를 본다', () => {
    /** `desktop:` 프리픽스가 실제로 켜지는지 — 요소를 만들어 계산된 스타일로 확인한다 */
    const desktopVariantMatches = () => {
      const el = document.createElement('div');
      el.className = 'hidden desktop:block';
      document.body.appendChild(el);
      const visible = getComputedStyle(el).display !== 'none';
      el.remove();
      return visible;
    };

    it('경계 바로 아래에서는 둘 다 모바일이다', async () => {
      await page.viewport(getMobileSize() - 1, 800);
      expect(matchMedia(getDesktopQuery()).matches).toBe(false);
      expect(desktopVariantMatches()).toBe(false);
    });

    it('경계에서는 둘 다 데스크톱이다', async () => {
      await page.viewport(getMobileSize(), 800);
      expect(matchMedia(getDesktopQuery()).matches).toBe(true);
      expect(desktopVariantMatches()).toBe(true);

      // 다른 테스트가 데스크톱 폭을 전제하므로 되돌린다
      await page.viewport(1280, 800);
    });
  });
});
