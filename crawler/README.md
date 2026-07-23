# Woojuin Crawler (Scrapling 사이드카)

Java 백엔드의 Jsoup 기반 `HtmlFetcher`가 **JS 렌더링 SPA·봇 차단(Cloudflare 등)**
페이지에서 빈 껍데기만 받아올 때, 폴백으로 호출되는 크롤링 서비스다.
[Scrapling](https://github.com/D4Vinci/Scrapling)의 `StealthyFetcher`(camoufox
스텔스 브라우저)로 실제 브라우저처럼 렌더한 최종 HTML을 돌려준다.

## 흐름

```
UrlItemProcessor / UrlBatchExportRunner
        │  HtmlFetcher.fetch(url)
        ▼
FallbackHtmlFetcher (@Primary)
        ├─ 1) JsoupHtmlFetcher      (빠른 경로: 정적 HTML)
        └─ 2) ScraplingHtmlFetcher  (폴백: Jsoup이 실패하거나 결과가 빈약할 때만)
                    │  POST /render {url}
                    ▼
              이 서비스 (StealthyFetcher) ──▶ {url, status, html}
```

Java는 받은 `html`을 `Jsoup.parse(html, url)`로 감싸 기존 OG 스크래퍼·본문
추출을 그대로 태운다. 브라우저는 느리고 무거워서 **폴백 경로에서만** 호출된다.

## API

- `GET /health` → `{"status":"ok"}`
- `POST /render` — body `{ "url": "...", "solve_cloudflare": true?, "network_idle": true? }`
  → `{ "url": "<최종 URL>", "status": 200, "html": "<렌더된 HTML>" }`
  - 실패 시 `502` (Java는 폴백 실패로 처리하고 Jsoup 결과로 되돌아간다)

## 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `CRAWLER_HEADLESS` | `true` | 헤드리스 브라우저 |
| `CRAWLER_NETWORK_IDLE` | `true` | 네트워크 유휴까지 대기 |
| `CRAWLER_SOLVE_CLOUDFLARE` | `true` | Cloudflare Turnstile 우회 시도(느려짐) |
| `CRAWLER_TIMEOUT_MS` | `30000` | 렌더 타임아웃(ms) |
| `CRAWLER_MAX_CONCURRENCY` | `2` | 동시 브라우저 수 상한 |

## 로컬 실행

```bash
# 도커 (권장 — 브라우저 의존성 포함)
docker compose up -d crawler

# 또는 직접
cd crawler
pip install -r requirements.txt
scrapling install          # 브라우저 다운로드 (최초 1회)
uvicorn main:app --host 0.0.0.0 --port 8001
```

## Java 쪽 연동 켜기

백엔드는 기본적으로 크롤러 폴백이 **꺼져 있다**(`CRAWLER_ENABLED=false`).
이 서비스를 띄운 뒤 백엔드 환경변수에서 켠다:

```
CRAWLER_ENABLED=true
CRAWLER_BASE_URL=http://localhost:8001
```
