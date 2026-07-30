from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT / "dataset" / "tester" / "정우현"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/chat"
OPENROUTER_MODEL = "qwen/qwen3-8b"
OLLAMA_MODEL = "qwen3:8b"


PROMPT = """당신은 사용자가 저장한 URL 콘텐츠의 제목과 요약을 정리하는 AI입니다.

작업:
1. 기존 제목이 콘텐츠를 구체적으로 설명하는 정상적인 제목인지 판단하세요.
2. 기존 제목이 정상적이면 그대로 유지하세요.
3. 기존 제목이 비어 있거나, "제목 없음"·"Untitled" 같은 임시 문구이거나,
   도메인명·앱스토어 주소·"- YouTube"처럼 일반적이면 콘텐츠를 나타내는 제목으로 교체하세요.
4. 기존 제목이 60자를 넘거나, SNS 본문·해시태그·홍보 문구가 제목에 통째로 들어간
   캡션형 제목이면 핵심 주제만 남긴 짧은 제목으로 교체하세요.
5. summary는 핵심 주제와 사용자가 다시 찾을 이유가 드러나는 한국어 1~2문장으로 작성하세요.

제목 규칙:
- 원문만 근거로 하고 원문에 없는 사실을 추가하지 마세요.
- 낚시성 표현, 불필요한 이모지, 사이트명 접미사를 제거하세요.
- 새 제목은 자연스러운 한국어 60자 이내로 간결하게 작성하세요.
- 저자명·제품명·작품명처럼 식별에 중요한 고유명사는 유지하세요.
- 기존 제목이 충분히 구체적이면 문체 개선만을 이유로 바꾸지 마세요.
- 제목이 지나치게 길면 내용의 핵심 대상과 목적만 남기고 해시태그와 부연 설명은 제거하세요.
- 정보가 부족해도 URL이나 도메인명만 제목으로 사용하지 말고, 확인 가능한 범위에서 작성하세요.

출력 규칙:
- titleAction은 KEEP 또는 REPLACE 중 하나입니다.
- KEEP이면 finalTitle은 existingTitle과 정확히 같아야 합니다.
- REPLACE이면 finalTitle은 새로 생성한 제목이어야 합니다.
- contentSufficient는 신뢰할 수 있는 제목과 요약을 만들 근거가 충분한지 나타냅니다.
- JSON 외의 설명이나 Markdown을 출력하지 마세요.

입력:
{content}

출력 형식:
{{"titleAction":"KEEP","finalTitle":"string","summary":"string","contentSufficient":true}}"""


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "titleAction": {"type": "string", "enum": ["KEEP", "REPLACE"]},
        "finalTitle": {"type": "string", "minLength": 1, "maxLength": 60},
        "summary": {"type": "string", "minLength": 1},
        "contentSufficient": {"type": "boolean"},
    },
    "required": ["titleAction", "finalTitle", "summary", "contentSufficient"],
}


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == "OPENROUTER_API_KEY" and key.strip() not in os.environ:
            os.environ[key.strip()] = value.strip().strip("\"'")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_compact_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def input_content(value: dict[str, Any], max_chars: int = 12000) -> str:
    preview = value.get("preview") or {}
    sections = [
        f"existingTitle: {value.get('title') or ''}",
        f"url: {value.get('url') or ''}",
        f"status: {value.get('status') or ''}",
    ]
    if preview.get("description"):
        sections.append(f"previewDescription: {preview['description']}")
    if value.get("content"):
        sections.append(f"content: {str(value['content'])[:max_chars]}")
    return "\n".join(sections)


def title_must_be_replaced(title: Any) -> bool:
    normalized = str(title or "").strip()
    return (
        not normalized
        or normalized.lower() in {"제목 없음", "untitled", "no title"}
        or len(normalized) > 60
        or normalized.lower() in {"- youtube", "apps.apple.com", "play.google.com"}
        or bool(
            re.fullmatch(
                r"(?:www\.)?[\w.-]+\.(?:com|co\.kr|kr|net|org)(?:/.*)?",
                normalized,
                flags=re.IGNORECASE,
            )
        )
    )


def extract_json(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def call_model(
    provider: str,
    api_key: str | None,
    prompt: str,
    retries: int = 5,
) -> dict[str, Any]:
    if provider == "openrouter":
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "reasoning": {"enabled": False},
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "url_metadata", "strict": True, "schema": SCHEMA},
            },
        }
        url = OPENROUTER_URL
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ssafy",
            "X-OpenRouter-Title": "Woojuin URL Metadata Evaluation",
        }
    else:
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False,
            "format": SCHEMA,
            "options": {"temperature": 0, "seed": 42, "num_ctx": 16384},
        }
        url = OLLAMA_URL
        headers = {"Content-Type": "application/json"}

    encoded = json.dumps(payload).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        request = Request(url, data=encoded, method="POST", headers=headers)
        try:
            started = time.perf_counter()
            with urlopen(request, timeout=240) as response:
                raw = json.loads(response.read().decode("utf-8"))
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            if provider == "openrouter":
                message = raw["choices"][0]["message"]["content"]
                usage = raw.get("usage")
                model = raw.get("model")
            else:
                message = raw["message"]["content"]
                usage = {
                    "prompt_tokens": raw.get("prompt_eval_count"),
                    "completion_tokens": raw.get("eval_count"),
                    "total_tokens": (raw.get("prompt_eval_count") or 0) + (raw.get("eval_count") or 0),
                }
                model = raw.get("model")
            return {
                "parsed": extract_json(message),
                "rawText": message,
                "usage": usage,
                "latencyMs": latency_ms,
                "model": model,
            }
        except (HTTPError, URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(min(2**attempt, 20))
    raise RuntimeError(f"모델 호출 실패: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["openrouter", "ollama"], required=True)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--enriched-dataset", type=Path)
    parser.add_argument("--shard-index", type=int)
    parser.add_argument("--shard-count", type=int, default=1)
    args = parser.parse_args()

    load_env(ROOT.parent.parent / ".env")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if args.provider == "openrouter" and not api_key:
        raise ValueError("OPENROUTER_API_KEY가 없습니다")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = (
        args.output or ROOT / "results" / f"{stamp}-{args.provider}-qwen3-8b-url-metadata"
    ).resolve()
    enriched = (
        args.enriched_dataset
        or ROOT / "dataset" / "tester" / f"정우현-{args.provider}-metadata"
    ).resolve()
    source_root = args.dataset.resolve()
    source_files = sorted(source_root.rglob("*.txt"))
    total_source_files = len(source_files)
    if args.shard_index is not None:
        if not 0 <= args.shard_index < args.shard_count:
            raise ValueError("shard-index는 0 이상 shard-count 미만이어야 합니다")
        source_files = source_files[args.shard_index :: args.shard_count]
    rows = []

    for index, source in enumerate(source_files, 1):
        relative = source.relative_to(source_root)
        checkpoint = output / "calls" / relative.with_suffix(".json")
        value = read_json(source)
        if checkpoint.exists():
            response = read_json(checkpoint)
        else:
            prompt = PROMPT.format(content=input_content(value))
            response = call_model(args.provider, api_key, prompt)
            write_json(checkpoint, response)

        result = response["parsed"]
        if title_must_be_replaced(value.get("title")) and result["titleAction"] != "REPLACE":
            correction_prompt = (
                PROMPT.format(content=input_content(value))
                + "\n\n기존 제목은 필수 교체 조건에 해당합니다. 반드시 titleAction을 REPLACE로 하고 "
                "원문의 핵심을 나타내는 60자 이내의 새 제목을 생성하세요."
            )
            response = call_model(args.provider, api_key, correction_prompt)
            result = response["parsed"]
            write_json(checkpoint, response)
        if result["titleAction"] == "KEEP":
            result["finalTitle"] = str(value.get("title") or result["finalTitle"])
        enriched_value = {
            **value,
            "title": result["finalTitle"],
            "summary": result["summary"],
        }
        write_compact_json(enriched / relative, enriched_value)
        rows.append(
            {
                "file": str(relative),
                "originalTitle": value.get("title"),
                **result,
                "titleChanged": result["finalTitle"] != value.get("title"),
                "latencyMs": response.get("latencyMs"),
                "usage": response.get("usage"),
            }
        )
        print(f"[{index}/{len(source_files)}] {relative}", flush=True)

    changed = sum(bool(row["titleChanged"]) for row in rows)
    sufficient = sum(bool(row["contentSufficient"]) for row in rows)
    summary = {
        "provider": args.provider,
        "model": OPENROUTER_MODEL if args.provider == "openrouter" else OLLAMA_MODEL,
        "items": len(rows),
        "titleChanged": changed,
        "titleKept": len(rows) - changed,
        "contentSufficient": sufficient,
        "contentInsufficient": len(rows) - sufficient,
        "shardIndex": args.shard_index,
        "shardCount": args.shard_count,
        "totalDatasetItems": total_source_files,
        "output": str(output),
        "enrichedDataset": str(enriched),
        "createdAt": datetime.now().astimezone().isoformat(),
    }
    suffix = f"-shard-{args.shard_index}" if args.shard_index is not None else ""
    write_json(output / f"metadata-results{suffix}.json", rows)
    write_json(output / f"summary{suffix}.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
