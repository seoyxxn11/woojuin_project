import { useEffect, useState } from 'react';
import { getDesktopQuery } from '@/constants/breakpoints';

/**
 * 데스크톱 폭인지 — 경계는 theme.css 의 `--breakpoint-sm` 이다.
 *
 * 노출·크기·배치는 전부 Tailwind `sm:` 으로 해결한다. 이 훅은 CSS 로 안 되는
 * 경우에만 쓴다 — 지금은 데스크톱 전용 화면의 라우트 가드가 유일하다.
 * (숨기는 것과 못 들어가게 막는 것은 다르다. 링크를 직접 열 수 있기 때문이다.)
 *
 * 초기값을 지연 계산으로 읽어야 첫 프레임에 잘못된 쪽이 번쩍이지 않는다.
 */
export function useIsDesktop(): boolean {
  const [isDesktop, setIsDesktop] = useState(() => window.matchMedia(getDesktopQuery()).matches);

  useEffect(() => {
    const mql = window.matchMedia(getDesktopQuery());
    const onChange = (e: MediaQueryListEvent) => setIsDesktop(e.matches);

    mql.addEventListener('change', onChange);
    setIsDesktop(mql.matches); // 구독 직전에 바뀌었을 수 있다
    return () => mql.removeEventListener('change', onChange);
  }, []);

  return isDesktop;
}
