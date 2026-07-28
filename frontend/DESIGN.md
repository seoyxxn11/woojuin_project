# 우주인(Woojuin) 디자인 시스템

> 출처: `우주인/v3.5/design-system.html` (스냅샷 2026-07-20)
> 스택: **Tailwind CSS v4** (`@tailwindcss/vite`) — CSS-first `@theme` 방식.
> 토큰 정의: [`src/styles/theme.css`](src/styles/theme.css)

컨셉: "정보를 전부 빨아들이는 우주" — 순수 블랙 우주 스테이지 위에 메모리를 별/별자리로 배치하는 다크 테마 워크스페이스.

---

## 1. 컬러

### Surface (배경 계층)

| 토큰 | HEX | Tailwind | 용도 |
|---|---|---|---|
| `--color-space` | `#0E1017` | `bg-space` | 우주 스테이지 — 최하단 배경(순수 블랙) |
| `--color-sidebar` | `#171923` | `bg-sidebar` | 사이드바 / 패널 |
| `--color-surface` | `#20242F` | `bg-surface` | 카드 · 커맨드바 표면 |
| `--color-surface-2` | `#2A2E3A` | `bg-surface-2` | 액티브 네비 · 호버 |
| `--color-surface-3` | `#343947` | `bg-surface-3` | 눌림 · 강조 표면 |

### Border

| 토큰 | HEX | Tailwind |
|---|---|---|
| `--color-border` | `#313543` | `border-border` |
| `--color-border-soft` | `#24272F` | `border-border-soft` |

### Text

| 토큰 | HEX | Tailwind | 용도 |
|---|---|---|---|
| `--color-text-1` | `#F0F2F6` | `text-text-1` | 본문 · 제목 (기본) |
| `--color-text-2` | `#B0B6C3` | `text-text-2` | 보조 텍스트 |
| `--color-text-3` | `#7B8290` | `text-text-3` | 캡션 · 라벨 · placeholder |

### Accent

| 토큰 | HEX | Tailwind | 용도 |
|---|---|---|---|
| `--color-accent` | `#7C6CF0` | `bg-accent` / `text-accent` | 프라이머리 액션 (send 버튼 등) |
| `--color-accent-hover` | `#8F80F5` | `bg-accent-hover` | accent 호버 |

### Star (별자리 팔레트 · 5색 순환 + white)

| 토큰 | HEX | Tailwind | 매핑 예시 |
|---|---|---|---|
| `--color-star-lavender` | `#C9B8FF` | `star-lavender` | #Ideas #Study |
| `--color-star-blue` | `#8FB4FF` | `star-blue` | #Architecture #Backend #OS |
| `--color-star-green` | `#B8E6A3` | `star-green` | #Travel #Jeju |
| `--color-star-orange` | `#F5B08A` | `star-orange` | #Seongsu |
| `--color-star-yellow` | `#F2D96B` | `star-yellow` | #Coffee |
| `--color-star-white` | `#F5F1E8` | `star-white` | 미분류 memory |

> **규칙**: 채도를 올리지 않는다. 글로우는 투명도·블러로만 표현하고 `box-shadow`는 **3~5px 이내**. 연결선은 `rgba(160,170,200,.28)` 1px.

---

## 2. 타이포그래피

폰트: **Pretendard** → `-apple-system, BlinkMacSystemFont, system-ui, sans-serif` (Tailwind `font-sans`).
기본 `line-height: 1.6`, `-webkit-font-smoothing: antialiased`.

| 역할 | size / weight | Tailwind |
|---|---|---|
| page-title | 34px / 800 · `-0.01em` | `text-display font-extrabold tracking-tight` |
| hero-title | `clamp(30px,4.5vw,44px)` / 800 | `text-hero font-extrabold` |
| card-title | 18px / 800 | `text-lg font-extrabold` |
| meta | 15px / 400 | `text-[15px]` |
| nav | 15px / 500 | `text-[15px] font-medium` |
| section-label | 12px / 700 · `.14em` UPPERCASE | `text-label font-bold tracking-[0.14em] uppercase` |
| star-label | 13px / 600 | `text-[13px] font-semibold` |
| body | 14.5px / 400 | `text-body` |
| subtitle | 15.5px / 400 | `text-[15.5px]` |

---

## 3. Radius

| 토큰 | 값 | Tailwind |
|---|---|---|
| `--radius-sm` | 8px | `rounded-sm` |
| `--radius-md` | 12px | `rounded-md` |
| `--radius-lg` | 16px | `rounded-lg` |
| `--radius-pill` | 999px | `rounded-pill` |

카드/모달은 상황에 따라 14·16·20px도 사용 (`rounded-[20px]` 등).

---

## 4. 그림자 (Elevation)

글로우 외 그림자는 모두 순수 블랙 기반. `theme.css`에 유틸 변수로 제공.

| 토큰 | 값 | 용도 |
|---|---|---|
| `--shadow-pop` | `0 14px 40px rgba(0,0,0,.6)` | 컨텍스트 메뉴 |
| `--shadow-float` | `0 20px 60px rgba(0,0,0,.6)` | 커맨드바 · 드롭다운 |
| `--shadow-modal` | `0 30px 80px rgba(0,0,0,.7)` | 모달 |
| `--shadow-tooltip` | `0 16px 50px rgba(0,0,0,.7)` | 별 툴팁 |

Tailwind: `shadow-pop` `shadow-float` `shadow-modal` `shadow-tooltip`.

---

## 5. 레이아웃 상수

| 토큰 | 값 | Tailwind |
|---|---|---|
| `--sidebar-w` | 300px | `w-sidebar` |
| collapsed sidebar | 72px | — |

---

## 6. 컴포넌트 레시피 (Tailwind 클래스 예시)

```html
<!-- 프라이머리 버튼 -->
<button class="inline-flex items-center gap-2 px-5 py-[11px] rounded-md
               bg-accent hover:bg-accent-hover text-white font-semibold
               text-sm transition-colors">
  전송
</button>

<!-- 고스트 버튼 -->
<button class="inline-flex items-center gap-2 px-5 py-[11px] rounded-md
               bg-surface hover:bg-surface-2 text-text-1 border border-border
               font-semibold text-sm transition-colors">
  취소
</button>

<!-- 카드 -->
<div class="bg-surface border border-border rounded-lg p-6 shadow-modal">…</div>

<!-- 네비 항목 (active) -->
<div class="flex items-center gap-3 px-3.5 py-[11px] rounded-md
            bg-surface-2 text-text-1 text-[15px] font-medium cursor-pointer">
  Personal Space
</div>

<!-- 별자리 태그 pill -->
<span class="inline-flex items-center gap-1.5 px-2.5 py-[3px] rounded-pill
             bg-surface-3 text-[11px] font-bold">
  <span class="w-1.5 h-1.5 rounded-full bg-star-blue"></span>#Backend
</span>

<!-- 상태 배지 -->
<span class="text-[11.5px] font-bold px-2.5 py-[3px] rounded-pill
             bg-star-green/10 text-star-green">완료</span>
```

---

## 7. 참고

- 배경은 항상 `bg-space` 위에 계층을 쌓는다 (sidebar → surface → surface-2/3).
- 우주인 캐릭터 PNG는 순수 블랙 배경 위에서만 사용. 밝은 배경에는 앱 아이콘 사용.
- 별/핀 글로우는 과하지 않게 (box-shadow 3~5px).
