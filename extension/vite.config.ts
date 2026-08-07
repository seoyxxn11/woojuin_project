import { defineConfig, Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * 그 빌드가 실제로 호출하는 호스트만 manifest 에 남긴다.
 *
 * manifest.json 은 정적 파일이라 모드에 따라 갈릴 수 없다. 그래서 세 환경의 호스트를 모두
 * 적어 두는데, 배포판에 개발 주소(localhost·dev)가 남으면 웹스토어 심사에서 "왜 필요한가"를
 * 되묻는다 — 호스트 권한은 이미 상세 검토 대상이라 게시가 지연된다. 실제 호출 대상은
 * client.ts 가 모드별로 API 하나뿐이므로 나머지는 지워도 기능이 같다.
 * (웹앱 origin 은 세션 물려받기가 주입에 쓰던 것 — 링크 코드 로그인(-498)으로 옮겨가며
 *  주입 자체가 사라져 목록에서도 걷었다. 승인 창은 창을 열 뿐이라 호스트 권한이 필요 없다.)
 */
const HOSTS_BY_MODE: Record<string, string[]> = {
  development: ['http://localhost:8080/*'],
  demo: ['https://api.dev.woojuin.store/*'],
  production: ['https://api.woojuin.store/*'],
};

function narrowHostPermissions(mode: string): Plugin {
  return {
    name: 'woojuin:narrow-host-permissions',
    apply: 'build',
    // manifest 는 public/ 복사물이라 번들이 다 쓰인 뒤에 손대야 한다
    writeBundle(options) {
      const allowed = HOSTS_BY_MODE[mode];
      if (!allowed) {
        this.warn(`알 수 없는 모드(${mode}) — host_permissions 를 그대로 둔다`);
        return;
      }
      const target = resolve(options.dir ?? 'dist', 'manifest.json');
      const manifest = JSON.parse(readFileSync(target, 'utf-8')) as { host_permissions?: string[] };
      if (!manifest.host_permissions) return;
      manifest.host_permissions = manifest.host_permissions.filter((o) => allowed.includes(o));
      writeFileSync(target, `${JSON.stringify(manifest, null, 2)}\n`);
      this.info(`host_permissions → ${manifest.host_permissions.join(', ')} (mode=${mode})`);
    },
  };
}

// MV3: popup(HTML) + background(서비스워커) 두 엔트리
export default defineConfig(({ mode }) => ({
  plugins: [react(), narrowHostPermissions(mode)],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  build: {
    // 공유 청크의 <link rel="modulepreload"> 를 만들지 않는다. 확장 팝업은 디스크에서
    // 뜨므로 미리읽기의 이득이 없고, 크롬이 preload 사본과 모듈 로더 사본을 다른
    // 세계(world)로 취급해 "cross-world extension resource mismatch — 미사용" 경고만
    // 남긴다. 기능엔 무해하지만 콘솔을 어지럽혀 진짜 문제를 가린다.
    modulePreload: false,
    rollupOptions: {
      input: {
        popup: resolve(__dirname, 'popup.html'),
        background: resolve(__dirname, 'src/background/index.ts'),
      },
      output: {
        entryFileNames: (chunk) =>
          chunk.name === 'background' ? 'background.js' : 'assets/[name]-[hash].js',
      },
    },
  },
}));
