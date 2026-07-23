"""
Scrapling 기반 크롤링 사이드카.

Java 백엔드의 Jsoup HtmlFetcher는 단순 HTTP GET이라, JS로 렌더링되는 SPA나
Cloudflare 같은 봇 차단이 걸린 사이트에서는 빈 껍데기/차단 페이지만 받아온다.
그럴 때 폴백으로 이 서비스를 호출한다 — StealthyFetcher(camoufox 스텔스 브라우저)로
실제 브라우저처럼 렌더한 최종 HTML을 그대로 돌려주면, Java 쪽은 그 HTML을
Jsoup.parse로 감싸 기존 OG 스크래퍼/본문 추출 파이프라인을 그대로 태운다.

브라우저는 무겁고 느려서(요청당 수 초) 폴백 경로에서만 호출된다. 동시에 뜨는
브라우저 수는 세마포어로 묶어 OOM을 막는다.
"""
import os
import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from scrapling.fetchers import StealthyFetcher

HEADLESS = os.getenv("CRAWLER_HEADLESS", "true").lower() != "false"
NETWORK_IDLE = os.getenv("CRAWLER_NETWORK_IDLE", "true").lower() != "false"
SOLVE_CLOUDFLARE = os.getenv("CRAWLER_SOLVE_CLOUDFLARE", "true").lower() != "false"
TIMEOUT_MS = int(os.getenv("CRAWLER_TIMEOUT_MS", "30000"))
MAX_CONCURRENCY = int(os.getenv("CRAWLER_MAX_CONCURRENCY", "2"))

# 배치 도구가 8병렬로 때려도 한 번에 뜨는 브라우저 수를 이만큼으로 묶어 메모리를 지킨다.
_slots = threading.BoundedSemaphore(MAX_CONCURRENCY)

app = FastAPI(title="Woojuin Crawler", version="0.1.0")


class RenderRequest(BaseModel):
    url: str
    # None이면 서버 기본값(env)을 쓴다. 호출부가 페이지별로 덮어쓸 수 있게 열어둔다.
    solve_cloudflare: bool | None = None
    network_idle: bool | None = None


class RenderResponse(BaseModel):
    url: str      # 리다이렉트까지 따라간 최종 URL (Jsoup baseUri로 쓰인다)
    status: int
    html: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/render", response_model=RenderResponse)
def render(req: RenderRequest):
    solve = SOLVE_CLOUDFLARE if req.solve_cloudflare is None else req.solve_cloudflare
    idle = NETWORK_IDLE if req.network_idle is None else req.network_idle

    # 엔드포인트를 async가 아닌 def로 두면 FastAPI가 스레드풀에서 실행한다 —
    # Scrapling.fetch는 블로킹이라 이벤트 루프를 막지 않게 이 편이 안전하다.
    with _slots:
        try:
            page = StealthyFetcher.fetch(
                req.url,
                headless=HEADLESS,
                solve_cloudflare=solve,
                network_idle=idle,
                timeout=TIMEOUT_MS,
            )
        except Exception as exc:  # noqa: BLE001 - 어떤 실패든 Java가 폴백 실패로 처리하도록 502로 변환
            raise HTTPException(status_code=502, detail=f"render failed: {exc}") from exc

    html = _html_of(page)
    if not html:
        raise HTTPException(status_code=502, detail="empty html")

    return RenderResponse(
        url=getattr(page, "url", None) or req.url,
        status=getattr(page, "status", 0) or 0,
        html=html,
    )


def _html_of(page) -> str:
    """Response에서 전체 HTML 문자열을 최대한 견고하게 뽑는다.

    브라우저 페처의 body는 보통 렌더된 DOM 문자열이지만 버전에 따라 bytes일 수
    있어 둘 다 처리하고, 비어 있으면 html_content로 한 번 더 시도한다.
    """
    raw = getattr(page, "body", None)
    if isinstance(raw, (bytes, bytearray)):
        encoding = getattr(page, "encoding", "utf-8") or "utf-8"
        html = raw.decode(encoding, errors="replace")
    else:
        html = raw or ""
    if not html:
        html = getattr(page, "html_content", "") or ""
    return html
