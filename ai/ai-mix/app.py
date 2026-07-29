from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from woojuin_ai.client import ConfigurationError, OpenRouterClient, OpenRouterError
from woojuin_ai.config import Settings, load_settings
from woojuin_ai.models import (
    ApiResponse,
    CategoryClassificationInput,
    CategoryClassificationOutput,
    CategoryDescriptionInput,
    CategoryDescriptionOutput,
    CoordinateReductionInput,
    CoordinateReductionOutput,
    EmbeddingBatchInput,
    EmbeddingBatchOutput,
    EmbeddingInput,
    EmbeddingOutput,
    HealthOutput,
    ImageAiSource,
    MemoAiSource,
    TitleSummaryOutput,
    UrlAiSource,
)
from woojuin_ai.service import AiMixService, InvalidModelResponse


app = FastAPI(
    title="Woojuin AI Mix",
    version="1.0.0",
    description="우주인 AI 단계별 OpenRouter 호출 서비스",
)


@lru_cache
def get_settings() -> Settings:
    return load_settings()


@lru_cache
def get_service() -> AiMixService:
    settings = get_settings()
    return AiMixService(OpenRouterClient(settings), settings)


def success(data: Any) -> dict[str, Any]:
    return {"status": 200, "message": "success", "data": data}


def error_response(status: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"status": status, "message": message, "data": None},
    )


@app.exception_handler(ConfigurationError)
def configuration_error_handler(_request: Request, exc: ConfigurationError) -> JSONResponse:
    return error_response(503, str(exc))


@app.exception_handler(OpenRouterError)
def openrouter_error_handler(_request: Request, exc: OpenRouterError) -> JSONResponse:
    return error_response(502, str(exc))


@app.exception_handler(InvalidModelResponse)
def invalid_model_response_handler(
    _request: Request, exc: InvalidModelResponse
) -> JSONResponse:
    return error_response(502, str(exc))


@app.exception_handler(RequestValidationError)
def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"] if part != "body")
        details.append(f"{location}: {error['msg']}")
    return error_response(422, "입력값이 올바르지 않습니다: " + " | ".join(details))


@app.get("/health", response_model=ApiResponse[HealthOutput])
def health(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    return success(
        HealthOutput(
            status="UP",
            api_key_configured=bool(settings.api_key),
            chat_model=settings.chat_model,
            embedding_model=settings.embedding_model,
        )
    )


@app.post(
    "/v1/title-summary/memo",
    response_model=ApiResponse[TitleSummaryOutput],
)
def title_summary_memo(
    source: MemoAiSource,
    service: AiMixService = Depends(get_service),
) -> dict[str, Any]:
    return success(service.create_title_summary("memo", source))


@app.post(
    "/v1/title-summary/url",
    response_model=ApiResponse[TitleSummaryOutput],
)
def title_summary_url(
    source: UrlAiSource,
    service: AiMixService = Depends(get_service),
) -> dict[str, Any]:
    return success(service.create_title_summary("url", source))


@app.post(
    "/v1/title-summary/image",
    response_model=ApiResponse[TitleSummaryOutput],
)
def title_summary_image(
    source: ImageAiSource,
    service: AiMixService = Depends(get_service),
) -> dict[str, Any]:
    return success(service.create_title_summary("image", source))


@app.post(
    "/v1/categories/classify",
    response_model=ApiResponse[CategoryClassificationOutput],
)
def classify_category(
    value: CategoryClassificationInput,
    service: AiMixService = Depends(get_service),
) -> dict[str, Any]:
    return success(service.classify_categories(value))


@app.post("/v1/embeddings", response_model=ApiResponse[EmbeddingOutput])
def create_embedding(
    value: EmbeddingInput,
    service: AiMixService = Depends(get_service),
) -> dict[str, Any]:
    return success(service.create_embeddings([value]).items[0])


@app.post(
    "/v1/embeddings/batch",
    response_model=ApiResponse[EmbeddingBatchOutput],
)
def create_embeddings(
    value: EmbeddingBatchInput,
    service: AiMixService = Depends(get_service),
) -> dict[str, Any]:
    return success(service.create_embeddings(value.items))


@app.post(
    "/v1/coordinates/reduce",
    response_model=ApiResponse[CoordinateReductionOutput],
)
def reduce_coordinates(
    value: CoordinateReductionInput,
    service: AiMixService = Depends(get_service),
) -> dict[str, Any]:
    return success(service.reduce_coordinates(value))


@app.post(
    "/v1/categories/description",
    response_model=ApiResponse[CategoryDescriptionOutput],
)
def create_category_description(
    value: CategoryDescriptionInput,
    service: AiMixService = Depends(get_service),
) -> dict[str, Any]:
    return success(service.create_category_description(value))
