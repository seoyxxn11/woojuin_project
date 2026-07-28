# 우주인 프론트엔드 — 폴더 구조 & 설계 전략

> 기술 스택: React 18 · TypeScript · Vite · Tailwind CSS v4 · React Router · TanStack Query · Jotai · PWA(Workbox)

---

## 1. 폴더 구조

```
frontend/src/
├─ assets/           # 이미지·폰트·SVG 등 정적 리소스
├─ components/
│  ├─ ui/            # 재사용 UI (도메인 모름) — 디자인 시스템
│  └─ domain/        # 우주인 전용 UI (도메인 앎)
├─ hooks/            # 커스텀 훅 (useXXX)
├─ layouts/          # 페이지 공통 레이아웃
├─ pages/            # 라우팅 단위 페이지 (한 화면 = 한 파일)
├─ routes/           # 라우터 설정 (React Router)
├─ services/         # API 요청 로직 (axios)
├─ stores/           # 전역 상태 (Jotai atom)
├─ styles/           # CSS · 디자인 토큰
├─ types/            # 공통 타입 정의
├─ utils/            # 유틸 함수·포맷터·헬퍼
├─ main.tsx          # 앱 엔트리 (Provider 조립)
└─ sw.ts             # 서비스워커 (Share Target · FCM)
```

### 폴더별 용도

| 폴더명 | 용도 |
| --- | --- |
| `assets/` | 이미지, 폰트, SVG 등 정적 리소스 (우주인 캐릭터 PNG, 브랜드 로고) |
| `components/ui/` | 재사용 가능한 작은 단위 UI 컴포넌트 (Button, Modal, Toast, Tag, Tooltip) |
| `components/domain/` | 우주인 도메인에 묶인 UI (ItemCard, StarTooltip, WorkspaceList) |
| `pages/` | 라우팅 단위 페이지 (랜딩, 로그인, 대시보드, 성좌뷰, 지도뷰, 휴지통, 마이페이지) |
| `hooks/` | 로직 재사용을 위한 커스텀 훅 (`useItems`, `useWorkspaces`, `useTheme`) |
| `utils/` | 유틸 함수, 포맷터, 헬퍼 함수 (날짜 포맷, 파일 크기 변환) |
| `routes/` | 라우터 설정 관련 파일 (React Router) |
| `layouts/` | 페이지 공통 레이아웃 컴포넌트 (AppShell, Sidebar, TopBar, CommandBar) |
| `stores/` | 전역 상태 관리 — **Jotai** (테마, 사이드바 접힘, 커맨드바 열림) |
| `services/` | API 요청 로직 (axios client, items·workspaces API) |
| `styles/` | CSS 파일 — **`theme.css` = 디자인 토큰 단일 소스** |
| `types/` | 공통 타입 정의 (`Item`, `Workspace`, `ItemStatus`) |

---

## 2. `components/` 를 ui / domain 으로 나누는 이유

성격이 완전히 다른 둘이 섞이면, 화면 9개를 만들었을 때 40여 개 파일에서
**무엇을 재사용해도 되는지** 알 수 없게 된다.

| | `components/ui/` | `components/domain/` |
| --- | --- | --- |
| 도메인 타입 | 모름 (`Item` import 금지) | 앎 |
| 재사용 | 어느 프로젝트에나 | 우주인 전용 |
| 예시 | Button, Modal, Toast, Tag | ItemCard, StarTooltip, WorkspaceList |

> **규칙**: `components/ui/` 는 `types/`·`services/` 를 import 하지 않는다.
> 이걸 어기는 순간 디자인 시스템이 아니라 앱 코드가 된다.

### 색상 prop 금지

```tsx
<Button color="#7C6CF0">   // ❌ 토큰 체계가 깨짐
<Button variant="primary"> // ✅ 색은 토큰(bg-accent)이 결정
```

디자인 시스템의 계약은 TS 인터페이스가 아니라 **CSS 토큰**이다.

---

## 3. 디자인 시스템 전략

```
토큰(styles/theme.css)  →  프리미티브(components/ui/)  →  조립(layouts/·pages/)
```

### 3-1. 토큰 단일 소스

색·radius·그림자는 오직 `styles/theme.css` 의 `@theme` 에만 정의한다.
컴포넌트에는 색 리터럴을 쓰지 않고 토큰 유틸만 사용한다.

```tsx
bg-sidebar   text-text-2   bg-surface-2   border-border-soft
shadow-modal rounded-md    from-accent    to-accent-hover
```

### 3-2. 테마 전환 = `data-theme` 속성 하나

```ts
document.documentElement.setAttribute('data-theme', 'light'); // 또는 'dark'
```

- `:root` = 다크(기본), `:root[data-theme="light"]` = 라이트
- 특정성 `(0,2,0) > (0,1,0)` 이라 런타임에 색만 교체된다
- 토큰 기반이므로 **컴포넌트 코드 수정 없이** 전 화면이 따라온다

### 3-3. 레이아웃은 한 번만 만든다

사이드바 · 상단바 · 커맨드바 · 모달은 9개 화면이 전부 동일하다.
화면마다 바뀌는 건 **가운데 스테이지 안쪽뿐**이므로 `layouts/` 에서 1회 구현해 공유한다.

---

## 4. 상태 관리 분리

| 종류 | 도구 | 위치 | 예시 |
| --- | --- | --- | --- |
| 서버 상태 | TanStack Query | `hooks/` | 유저 정보(`useUser`), 저장 항목 목록, 처리 상태 폴링 |
| 특정 트리 안의 UI 상태 | Context | `stores/context/` | 사이드바 접힘·선택 항목(`SideBarContext`) |
| 앱 전역 UI 상태 | Jotai | `stores/` | 테마, 커맨드바 열림 |

서버에서 오는 데이터를 Jotai 에 복사해두지 않는다. 캐시 무효화가 이중으로 꼬인다.

**Context 와 Jotai 의 기준**: 그 상태가 특정 컴포넌트 트리 밖에서도 의미가 있는가.
사이드바 접힘은 `<SideBar>` 안에서만 쓰이므로 Context 로 범위를 가둔다 —
전역 스토어에 올리면 어디서나 접근 가능해져 소유자가 사라진다.
반대로 커맨드바처럼 여러 화면이 공유하는 상태는 Jotai 가 맞다.

**서버 상태는 훅 하나로 감싼다.** 컴포넌트가 목 데이터를 직접 import 하면
연동 시 소비처를 전부 고쳐야 한다. `useUser()` 처럼 진입점을 만들어 두면 그 파일만 바꾸면 된다.

---

## 5. import 방향

```
pages  →  layouts · components · hooks · services
components/domain  →  components/ui · types
components/ui  →  (아무 도메인도 import 하지 않음)
```

- 역방향 import 금지 (`components` 가 `pages` 를 참조하면 순환·재사용 불가)
- `services/` 는 API 응답 봉투(`ApiResponse<T>`)를 **벗겨서** 반환한다.
  화면은 전송 형식을 몰라야 한다. (현재 `res.data.data` 반환 방식 유지)

---

## 6. 목업 → 페이지 매핑

디자인 원본: `우주인/v3.5/` (다크) · `우주인/v3.5-white/` (다크·라이트 토글)

| 목업 파일 | 라우트 | 비고 |
| --- | --- | --- |
| `landing.html` | `/` | |
| `login.html` | `/login` | |
| `dashboard.html` | `/w/:id` | 저장 항목 그리드 |
| `my-universe.html` | `/w/:id/universe` | **WebGL 성좌뷰** |
| `map-view.html` | `/w/:id/map` | |
| `canvas-view.html` | `/w/:id/canvas` | |
| `trash-view.html` | `/w/:id/trash` | |
| `mypage.html` | `/me` | |
| `uju-assistant.html` | 오버레이 | 페이지 아님 |
| `design-system.html` | — | 토큰·컴포넌트 사양 참고용 |
| — | `/share-target` | PWA Web Share Target 진입점 |

---

## 7. 완료된 구조 이동

| 이전 | 현재 |
| --- | --- |
| `src/shared/api/client.ts` | `src/services/client.ts` |
| `src/shared/api/items.ts` | `src/services/items.ts` (타입은 `types/item.ts`) |
| `src/router.tsx` | `src/routes/router.tsx` |
| `src/index.css` | `src/styles/index.css` (+ `theme.css` import) |

### 네이밍

사이드바 관련은 **`SideBar`** 로 통일한다 (`SideBar.tsx` · `SideBarContext` · `useSideBar` · `sideBarClosed`).
단, `components/ui/` 의 범용 컴포넌트는 사이드바를 몰라야 하므로
`NavItem` 의 prop 은 `collapsed` 로 둔다 — 호출부에서 `collapsed={sideBarClosed}` 로 넘긴다.

---

## 8. 나중에 고려할 것 (지금은 하지 않음)

- **`features/` 도입** — 도메인별로 `api·hooks·components` 를 한 폴더에 묶는 방식.
  `components/domain/` 이 감당 안 될 만큼 커지면 그때 쪼갠다. 언제든 가능한 리팩터링이므로 미리 나누지 않는다.
- **DTO ↔ 도메인 모델 분리** — 서버 응답과 화면 모델이 실제로 어긋날 때
  (`createdAt: string → Date` 등) 해당 필드만 매핑한다. 지금은 모양이 같아 보일러플레이트만 는다.
- **Sidebar 합성 분해** — 두 번째 소비처(모바일 레이아웃)가 생길 때
  `<Sidebar.Nav>` `<Sidebar.Storage>` 형태로 쪼갠다.
