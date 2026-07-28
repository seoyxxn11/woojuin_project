import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import path from 'node:path';

// PWA: injectManifest 전략 사용
// 이유: Web Share Target(공유하기 연동) 처리 + FCM 백그라운드 수신 등
//       커스텀 서비스워커 로직이 필요함 (src/sw.ts)
export default defineConfig({
  // .env.example처럼 프론트/백엔드가 레포 루트 .env 하나를 같이 쓰는 구조라서,
  // Vite 기본값(frontend/.env)이 아니라 루트를 보게 한다. 안 그러면
  // VITE_API_BASE_URL 등이 매번 undefined로 읽힌다.
  envDir: path.resolve(__dirname, '..'),
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.ts',
      registerType: 'prompt',
      devOptions: { enabled: true, type: 'module' },
      manifest: {
        name: '우주인 — 올인원 AI 스크랩북',
        short_name: '우주인',
        description: '저장은 1초, 정리는 AI가, 찾을 땐 검색 한 번',
        lang: 'ko',
        start_url: '/',
        display: 'standalone',
        background_color: '#0b0f1e',
        theme_color: '#0b0f1e',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
          {
            src: '/icons/icon-512-maskable.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
        // Web Share Target (FR-013): Android에서 OS 공유 시트에 '우주인' 노출
        // PWA를 홈 화면에 설치해야 WebAPK로 등록됨. iOS 미지원(클립보드 감지로 보완)
        share_target: {
          action: '/share-target',
          method: 'GET',
          params: { title: 'title', text: 'text', url: 'url' },
        },
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8080',
    },
  },
});
