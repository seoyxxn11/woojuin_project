from __future__ import annotations

import argparse
import platform
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.dataset_loader import load_categories, load_memo_dataset
from src.embedding_pipeline import (
    build_coordinate_rows,
    build_embedding_text,
    embedding_usage,
    extract_embedding_vectors,
    input_hash,
    reduce_embeddings_to_3d,
)
from src.providers import sanitize_error
from src.result_writer import append_jsonl, read_jsonl, write_csv, write_json
from src.settings import load_settings


ROOT = Path(__file__).resolve().parent
RESULTS_ROOT = ROOT / "results" / "4차 임베딩 시각화"
DEFAULT_MODEL = "text-embedding-3-small"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="메모를 text-embedding-3-small로 임베딩하고 UMAP 3차원 좌표로 변환"
    )
    parser.add_argument("--limit", type=int, help="앞에서부터 처리할 메모 수")
    parser.add_argument("--test-ids", nargs="+", help="처리할 TEXT-001 형식의 ID")
    parser.add_argument("--resume", help="중단된 결과 폴더를 지정해 이어서 실행")
    parser.add_argument("--dry-run", action="store_true", help="API 호출과 결과 저장 없이 계획만 확인")
    parser.add_argument("--batch-size", type=int, help="API 요청 한 번에 보낼 메모 수")
    parser.add_argument("--dimensions", type=int, help="API가 지원할 경우 사용할 임베딩 차원")
    parser.add_argument("--n-neighbors", type=int, help="UMAP 이웃 수")
    parser.add_argument("--min-dist", type=float, help="UMAP 최소 거리")
    parser.add_argument("--metric", help="UMAP 거리 함수 (기본 cosine)")
    parser.add_argument("--random-state", type=int, help="UMAP 재현용 난수 시드")
    return parser.parse_args(argv)


def load_config() -> dict[str, Any]:
    value = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8")) or {}
    return value


def embedding_options(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    configured = config.get("embedding", {})
    umap_config = configured.get("umap", {})
    options = {
        "model": str(configured.get("model", DEFAULT_MODEL)),
        "batchSize": args.batch_size or int(configured.get("batchSize", 64)),
        "dimensions": args.dimensions,
        "nNeighbors": args.n_neighbors or int(umap_config.get("nNeighbors", 15)),
        "minDist": args.min_dist if args.min_dist is not None else float(umap_config.get("minDist", 0.1)),
        "metric": args.metric or str(umap_config.get("metric", "cosine")),
        "randomState": args.random_state if args.random_state is not None else int(umap_config.get("randomState", 42)),
    }
    if options["model"] != DEFAULT_MODEL:
        raise ValueError(f"이 실행기는 {DEFAULT_MODEL}만 사용합니다: {options['model']}")
    if options["batchSize"] < 1:
        raise ValueError("batch-size는 1 이상이어야 합니다")
    if options["dimensions"] is not None and options["dimensions"] < 1:
        raise ValueError("dimensions는 1 이상이어야 합니다")
    return options


def load_items(args: argparse.Namespace) -> list[dict[str, Any]]:
    memo_root = ROOT / "dataset" / "memo"
    items = load_memo_dataset(memo_root, load_categories(memo_root))
    if args.test_ids:
        requested = set(args.test_ids)
        unknown = requested - {item["testId"] for item in items}
        if unknown:
            raise ValueError(f"없는 testId: {sorted(unknown)}")
        items = [item for item in items if item["testId"] in requested]
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("limit는 1 이상이어야 합니다")
        items = items[:args.limit]
    if not items:
        raise ValueError("처리할 메모가 없습니다")
    return items


def unique_output_dir() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = RESULTS_ROOT / timestamp
    suffix = 1
    while candidate.exists():
        candidate = RESULTS_ROOT / f"{timestamp}-{suffix}"
        suffix += 1
    return candidate


def load_cached_embeddings(
    cache_path: Path,
    items: list[dict[str, Any]],
    model: str,
) -> dict[str, dict[str, Any]]:
    if not cache_path.exists():
        return {}
    current = {item["testId"]: input_hash(build_embedding_text(item)) for item in items}
    cached: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(cache_path):
        test_id = str(row.get("testId", ""))
        if test_id not in current:
            continue
        if row.get("model") != model:
            raise ValueError(f"{test_id}: 재개 데이터의 임베딩 모델이 다릅니다")
        if row.get("inputHash") != current[test_id]:
            raise ValueError(f"{test_id}: 재개 후 메모 내용이 변경되었습니다")
        vector = row.get("embedding")
        if not isinstance(vector, list) or not vector:
            raise ValueError(f"{test_id}: 저장된 임베딩 벡터가 올바르지 않습니다")
        cached[test_id] = row
    return cached


def request_embeddings(
    client: Any,
    *,
    model: str,
    texts: list[str],
    dimensions: int | None,
    max_retries: int = 2,
) -> tuple[list[list[float]], dict[str, int | None], str | None]:
    kwargs: dict[str, Any] = {
        "model": model,
        "input": texts,
        "encoding_format": "float",
    }
    if dimensions is not None:
        kwargs["dimensions"] = dimensions
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = client.embeddings.create(**kwargs)
            vectors = extract_embedding_vectors(response, len(texts))
            return vectors, embedding_usage(response), getattr(response, "_request_id", None)
        except Exception as exc:
            last_error = exc
            status = getattr(exc, "status_code", None)
            retriable = type(exc).__name__ in {
                "RateLimitError", "APITimeoutError", "APIConnectionError", "TimeoutError"
            } or (isinstance(status, int) and status >= 500)
            if not retriable or attempt >= max_retries:
                raise
            time.sleep(2**attempt)
    raise RuntimeError(str(last_error or "임베딩 요청 실패"))


def create_client(config: dict[str, Any]) -> tuple[Any, str, str]:
    openai_config = config.get("openai", {})
    key_env = str(openai_config.get("apiKeyEnv", "GMS_KEY"))
    api_key = load_settings(ROOT).key_for(key_env)
    if not api_key:
        raise ValueError(f"{key_env}가 설정되어 있지 않습니다")
    base_url = str(openai_config.get("baseUrl", "")).strip()
    from openai import OpenAI
    kwargs: dict[str, Any] = {"api_key": api_key, "max_retries": 0}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs), key_env, base_url or "default"


def write_metadata(
    output_dir: Path,
    *,
    status: str,
    items: list[dict[str, Any]],
    options: dict[str, Any],
    key_env: str,
    base_url: str,
    cached_count: int,
    request_count: int,
    token_usage: dict[str, int],
    embedding_dimensions: int | None = None,
    effective_neighbors: int | None = None,
    error: str | None = None,
) -> None:
    write_json(output_dir / "run-metadata.json", {
        "status": status,
        "createdAt": datetime.now().astimezone().isoformat(),
        "pythonVersion": platform.python_version(),
        "model": options["model"],
        "itemCount": len(items),
        "batchSize": options["batchSize"],
        "requestedDimensions": options["dimensions"],
        "embeddingDimensions": embedding_dimensions,
        "apiKeyEnv": key_env,
        "baseUrl": base_url,
        "cachedItemCount": cached_count,
        "apiRequestCount": request_count,
        "usage": token_usage,
        "umap": {
            "nComponents": 3,
            "nNeighbors": options["nNeighbors"],
            "effectiveNNeighbors": effective_neighbors,
            "minDist": options["minDist"],
            "metric": options["metric"],
            "randomState": options["randomState"],
        },
        "error": error,
    })


def run(args: argparse.Namespace) -> Path | None:
    config = load_config()
    options = embedding_options(config, args)
    items = load_items(args)
    batch_count = (len(items) + options["batchSize"] - 1) // options["batchSize"]
    key_env = str(config.get("openai", {}).get("apiKeyEnv", "GMS_KEY"))
    key_configured = load_settings(ROOT).key_configured(key_env)
    print(f"[OK] 모델: {options['model']}")
    print(f"[OK] 메모: {len(items)}개")
    print(f"[OK] 배치: 최대 {options['batchSize']}개, 신규 실행 기준 {batch_count}회 요청")
    print(f"[OK] API 키: {key_env} {'configured' if key_configured else 'missing'}")
    print(
        f"[OK] UMAP: 3차원, n_neighbors={options['nNeighbors']}, "
        f"min_dist={options['minDist']}, metric={options['metric']}"
    )
    if args.dry_run:
        print("[DRY-RUN] API를 호출하지 않았고 결과 파일도 만들지 않았습니다")
        return None

    output_dir = Path(args.resume).resolve() if args.resume else unique_output_dir()
    if args.resume and not output_dir.is_dir():
        raise ValueError(f"재개할 결과 폴더가 없습니다: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_path = output_dir / "raw" / "embeddings.jsonl"
    cached = load_cached_embeddings(cache_path, items, options["model"])
    client, key_env, base_url = create_client(config)
    request_count = 0
    token_usage = {"promptTokens": 0, "totalTokens": 0}
    write_metadata(
        output_dir, status="IN_PROGRESS", items=items, options=options,
        key_env=key_env, base_url=base_url, cached_count=len(cached),
        request_count=request_count, token_usage=token_usage,
    )

    pending = [item for item in items if item["testId"] not in cached]
    try:
        for start in range(0, len(pending), options["batchSize"]):
            batch = pending[start:start + options["batchSize"]]
            texts = [build_embedding_text(item) for item in batch]
            print(
                f"[API {request_count + 1}] "
                f"{batch[0]['testId']} ~ {batch[-1]['testId']} ({len(batch)}개)"
            )
            vectors, usage, request_id = request_embeddings(
                client,
                model=options["model"],
                texts=texts,
                dimensions=options["dimensions"],
            )
            request_count += 1
            for name in token_usage:
                token_usage[name] += usage.get(name) or 0
            for item, text, vector in zip(batch, texts, vectors, strict=True):
                row = {
                    "testId": item["testId"],
                    "model": options["model"],
                    "inputHash": input_hash(text),
                    "embedding": vector,
                    "requestId": request_id,
                }
                append_jsonl(cache_path, row)
                cached[item["testId"]] = row
            write_metadata(
                output_dir, status="IN_PROGRESS", items=items, options=options,
                key_env=key_env, base_url=base_url, cached_count=len(cached),
                request_count=request_count, token_usage=token_usage,
            )

        vectors = [cached[item["testId"]]["embedding"] for item in items]
        coordinates, effective_neighbors = reduce_embeddings_to_3d(
            vectors,
            n_neighbors=options["nNeighbors"],
            min_dist=options["minDist"],
            metric=options["metric"],
            random_state=options["randomState"],
        )
        coordinate_rows = build_coordinate_rows(items, coordinates)
        embedding_rows = [
            {
                "testId": item["testId"],
                "title": item.get("title", ""),
                "category": item.get("expected", {}).get("categories", [""])[0],
                "sourcePath": item.get("sourcePath", ""),
                "embedding": cached[item["testId"]]["embedding"],
            }
            for item in items
        ]
        write_json(output_dir / "embeddings.json", embedding_rows)
        write_json(output_dir / "umap-3d.json", coordinate_rows)
        write_csv(
            output_dir / "umap-3d.csv",
            coordinate_rows,
            ["testId", "title", "category", "sourcePath", "x", "y", "z"],
        )
        write_metadata(
            output_dir, status="COMPLETED", items=items, options=options,
            key_env=key_env, base_url=base_url, cached_count=len(cached),
            request_count=request_count, token_usage=token_usage,
            embedding_dimensions=len(vectors[0]), effective_neighbors=effective_neighbors,
        )
    except Exception as exc:
        secret = load_settings(ROOT).key_for(key_env)
        message = sanitize_error(exc, (secret or "",))
        write_metadata(
            output_dir, status="FAILED", items=items, options=options,
            key_env=key_env, base_url=base_url, cached_count=len(cached),
            request_count=request_count, token_usage=token_usage, error=message,
        )
        raise RuntimeError(message) from exc

    print(f"[OK] 임베딩 차원: {len(vectors[0])}")
    print(f"[OK] 결과: {output_dir}")
    return output_dir


def main(argv: list[str] | None = None) -> int:
    try:
        run(parse_args(argv))
        return 0
    except (ValueError, RuntimeError) as exc:
        print(f"[ERROR] {sanitize_error(exc)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
