from __future__ import annotations

import asyncio
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, File, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from image_service import (
    ImageAiError,
    ImageAiErrorCode,
    ImageAnalysisResponse,
    ImageAnalysisService,
    build_http_payload,
)
from image_service.processing import MAX_SOURCE_BYTES
from providers import OllamaVisionProvider


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.qwen3vl8b.fast.yaml"
app = FastAPI(title="Woojuin Image AI", version="1.0.0")
inference_semaphore = asyncio.Semaphore(1)


@lru_cache(maxsize=1)
def get_service() -> ImageAnalysisService:
    with CONFIG_PATH.open(encoding="utf-8") as file:
        config = yaml.safe_load(file)
    prompt_path = ROOT / config["benchmark"]["prompt"]
    prompt = prompt_path.read_text(encoding="utf-8")
    return ImageAnalysisService(
        OllamaVisionProvider(config["model"]),
        prompt,
        max_attempts=2,
        max_dimension=int(config["benchmark"].get("max_dimension", 2048)),
    )


def failure_payload(
    code: ImageAiErrorCode,
    message: str,
    *,
    retryable: bool = False,
) -> dict[str, Any]:
    return build_http_payload(
        ImageAnalysisResponse(
            success=False,
            result=None,
            error_code=code.value,
            error_message=message,
            retryable=retryable,
        )
    )


@app.get("/health")
async def health() -> Any:
    service = get_service()
    try:
        await run_in_threadpool(service.validate_environment)
    except ImageAiError as exc:
        return JSONResponse(
            status_code=503,
            content=failure_payload(
                exc.code,
                str(exc),
                retryable=exc.retryable,
            ),
        )
    return {"status": "UP", "model": service.provider.model_id}


@app.post("/warmup")
async def warmup() -> Any:
    try:
        async with inference_semaphore:
            metadata = await run_in_threadpool(get_service().warmup)
    except ImageAiError as exc:
        return JSONResponse(
            status_code=503,
            content=failure_payload(
                exc.code,
                str(exc),
                retryable=exc.retryable,
            ),
        )
    return {"status": "READY", **metadata}


@app.post("/v1/images/analyze")
async def analyze_image(file: UploadFile = File(...)) -> Any:
    image_bytes = await file.read(MAX_SOURCE_BYTES + 1)
    if len(image_bytes) > MAX_SOURCE_BYTES:
        return JSONResponse(
            status_code=413,
            content=failure_payload(
                ImageAiErrorCode.IMAGE_TOO_LARGE,
                f"이미지는 {MAX_SOURCE_BYTES // (1024 * 1024)}MB 이하여야 합니다.",
            ),
        )
    if not image_bytes:
        return JSONResponse(
            status_code=400,
            content=failure_payload(
                ImageAiErrorCode.IMAGE_DECODE_FAILED,
                "빈 이미지 파일은 분석할 수 없습니다.",
            ),
        )

    suffix = Path(file.filename or "upload.jpg").suffix or ".jpg"
    with tempfile.TemporaryDirectory() as directory:
        image_path = Path(directory) / f"upload{suffix}"
        image_path.write_bytes(image_bytes)
        async with inference_semaphore:
            response = await run_in_threadpool(get_service().analyze, image_path)

    payload = build_http_payload(response)
    if not response.success:
        return JSONResponse(
            status_code=503 if response.retryable else 422,
            content=payload,
        )
    return payload
