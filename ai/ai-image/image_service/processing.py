from __future__ import annotations

import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image, ImageOps, UnidentifiedImageError

from .errors import ImageAiError, ImageAiErrorCode
from .models import ImageAnalysisResult


SUPPORTED_FORMATS = {"JPEG", "MPO", "PNG", "WEBP"}
MAX_SOURCE_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_DIMENSION = 2048
REQUIRED_FIELDS = {
    "title",
    "description",
    "tags",
    "ocr_text",
    "objects",
    "confidence",
}


def _gps_coordinate(value: Any, reference: Any) -> float | None:
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        return None
    try:
        degrees, minutes, seconds = (float(part) for part in value)
        coordinate = degrees + minutes / 60 + seconds / 3600
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    if str(reference).upper() in {"S", "W"}:
        coordinate *= -1
    return round(coordinate, 7)


def extract_image_metadata(image: Image.Image) -> dict[str, Any]:
    exif = image.getexif()
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo) if exif else {}
    latitude = _gps_coordinate(gps.get(2), gps.get(1)) if gps else None
    longitude = _gps_coordinate(gps.get(4), gps.get(3)) if gps else None
    captured_at = (exif.get(36867) or exif.get(306)) if exif else None
    if isinstance(captured_at, str):
        captured_at = captured_at.replace(":", "-", 2).replace(" ", "T", 1)
    return {
        "latitude": latitude,
        "longitude": longitude,
        "captured_at": captured_at,
    }


def prepare_image(
    image_path: Path,
    *,
    max_dimension: int = DEFAULT_MAX_DIMENSION,
    max_source_bytes: int = MAX_SOURCE_BYTES,
) -> tuple[bytes, dict[str, Any]]:
    if not image_path.is_file():
        raise ImageAiError(ImageAiErrorCode.IMAGE_NOT_FOUND, "이미지 파일을 찾을 수 없습니다.")
    source_size = image_path.stat().st_size
    if source_size > max_source_bytes:
        raise ImageAiError(
            ImageAiErrorCode.IMAGE_TOO_LARGE,
            f"이미지는 {max_source_bytes // (1024 * 1024)}MB 이하여야 합니다.",
        )

    try:
        with Image.open(image_path) as source:
            source.load()
            source_format = str(source.format or "").upper()
            if source_format not in SUPPORTED_FORMATS:
                raise ImageAiError(
                    ImageAiErrorCode.UNSUPPORTED_IMAGE,
                    f"지원하지 않는 이미지 형식입니다: {source_format or 'UNKNOWN'}",
                )
            original_size = source.size
            source_metadata = extract_image_metadata(source)
            image = ImageOps.exif_transpose(source)
            image = image.convert("RGB")
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            resized = image.size != original_size
            output = BytesIO()
            image.save(output, format="JPEG", quality=90, optimize=True)
    except ImageAiError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageAiError(
            ImageAiErrorCode.IMAGE_DECODE_FAILED,
            "이미지를 읽거나 변환할 수 없습니다.",
        ) from exc

    prepared = output.getvalue()
    return prepared, {
        "original_image_bytes": source_size,
        "sent_image_bytes": len(prepared),
        "original_width": original_size[0],
        "original_height": original_size[1],
        "sent_width": image.size[0],
        "sent_height": image.size[1],
        "image_resized": resized,
        "image_resize_policy": f"max_{max_dimension}px",
        "source_format": source_format,
        "sent_format": "JPEG",
        **source_metadata,
    }


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ImageAiError(
                ImageAiErrorCode.INVALID_MODEL_RESPONSE,
                "모델 응답에서 JSON 객체를 찾을 수 없습니다.",
                retryable=True,
            )
        try:
            value = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ImageAiError(
                ImageAiErrorCode.INVALID_MODEL_RESPONSE,
                "모델 응답 JSON이 완전하지 않습니다.",
                retryable=True,
            ) from exc
    if not isinstance(value, dict):
        raise ImageAiError(
            ImageAiErrorCode.INVALID_MODEL_RESPONSE,
            "모델 응답은 JSON 객체여야 합니다.",
            retryable=True,
        )
    return value


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[ \t]+", " ", value).strip()


def _clean_ocr(value: Any) -> str:
    text = _clean_text(value)
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        key = line.casefold()
        if line and key not in seen:
            seen.add(key)
            lines.append(line)
    return "\n".join(lines)


def _clean_list(value: Any, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_text(item)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def normalize_result(value: dict[str, Any]) -> ImageAnalysisResult:
    missing = REQUIRED_FIELDS - value.keys()
    if missing:
        raise ImageAiError(
            ImageAiErrorCode.INVALID_MODEL_RESPONSE,
            f"모델 응답 필드가 누락되었습니다: {sorted(missing)}",
            retryable=True,
        )
    confidence = value.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ImageAiError(
            ImageAiErrorCode.INVALID_MODEL_RESPONSE,
            "confidence는 0과 1 사이의 숫자여야 합니다.",
            retryable=True,
        )
    title = _clean_text(value.get("title"))
    description = _clean_text(value.get("description"))
    if not title or not description:
        raise ImageAiError(
            ImageAiErrorCode.INVALID_MODEL_RESPONSE,
            "title과 description은 비어 있을 수 없습니다.",
            retryable=True,
        )
    return ImageAnalysisResult(
        title=title,
        description=description,
        tags=_clean_list(value.get("tags"), limit=10),
        ocr_text=_clean_ocr(value.get("ocr_text")),
        objects=_clean_list(value.get("objects"), limit=10),
        confidence=max(0.0, min(1.0, float(confidence))),
    )
