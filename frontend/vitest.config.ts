import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { playwright } from '@vitest/browser-playwright';
import path from 'node:path';

/**
 * 테스트는 실제 Chromium 에서 돌린다(browser mode).
 * jsdom 은 CSS 레이아웃 엔진이 없어 getBoundingClientRect 가 전부 0 이라
 * "접으면 72px", "하위 항목이 4px 들여쓰기" 같은 검증을 할 수 없다.
 *
 * PWA 플러그인은 테스트에 불필요하므로 vite.config.ts 를 상속하지 않고 별도 설정한다.
 */
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
  test: {
    include: ['src/**/*.test.{ts,tsx}'],
    setupFiles: ['./src/test/setup.ts'],
    browser: {
      enabled: true,
      provider: playwright(),
      headless: true,
      // 기본은 데스크톱(>= lg). 사이드바 300px·팝오버 앵커처럼 lg 이상을 전제한 검증이 많다.
      // 모바일 동작은 각 테스트에서 page.viewport() 로 줄여서 확인한다.
      viewport: { width: 1280, height: 800 },
      instances: [
        {
          browser: 'chromium',
          // 기본값인 chrome-headless-shell 대신 일반 Chromium 을 쓴다.
          // headless shell 은 서명이 낯설어 보안 프로그램에 차단되는 경우가 있고,
          // 그때 Playwright 가 "Executable doesn't exist" 로 잘못 보고한다.
          launch: { channel: 'chromium' },
        },
      ],
    },
  },
});
