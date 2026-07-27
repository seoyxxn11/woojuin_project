# 이미지 AI 입출력 계약

## 입력

- 파일 형식: JPEG, PNG, WEBP
- 최대 원본 크기: 20MB
- 전처리: EXIF 회전 보정, RGB 변환, 최대 2048px 비율 유지 리사이즈
- 이미지 모델: `qwen3-vl:8b-instruct`
- 이미지 모델은 카테고리를 선택하지 않는다.

## 성공 응답

```json
{
  "success": true,
  "result": {
    "title": "이미지의 핵심 제목",
    "description": "핵심 내용과 시각·OCR 근거",
    "tags": ["검색 태그"],
    "ocr_text": "의미 있는 실제 텍스트",
    "objects": ["주요 객체"],
    "confidence": 0.95
  },
  "error_code": null,
  "error_message": null,
  "retryable": false,
  "metadata": {
    "model": "qwen3-vl:8b-instruct",
    "attempts": 1,
    "latitude": 35.1595,
    "longitude": 126.8526,
    "captured_at": "2026-07-17T23:29:29"
  }
}
```

좌표와 촬영시간은 모델 추정값이 아니라 원본 이미지 EXIF에서만 읽는다. EXIF 정보가 없으면 각 값은 `null`이다.

## 실패 응답

```json
{
  "success": false,
  "result": null,
  "error_code": "OLLAMA_UNAVAILABLE",
  "error_message": "Ollama에 연결할 수 없습니다.",
  "retryable": true,
  "metadata": {}
}
```

## 오류 코드

| 코드 | 재시도 | 설명 |
| --- | ---: | --- |
| `IMAGE_NOT_FOUND` | X | 이미지 파일 없음 |
| `UNSUPPORTED_IMAGE` | X | 지원하지 않는 이미지 형식 |
| `IMAGE_TOO_LARGE` | X | 원본 이미지 크기 초과 |
| `IMAGE_DECODE_FAILED` | X | 손상되거나 읽을 수 없는 이미지 |
| `OLLAMA_UNAVAILABLE` | O | Ollama 연결 실패 |
| `MODEL_NOT_INSTALLED` | X | 모델 미설치 |
| `MODEL_TIMEOUT` | O | 모델 요청 시간 초과 |
| `EMPTY_MODEL_RESPONSE` | O | 모델 빈 응답 |
| `INVALID_MODEL_RESPONSE` | O | JSON 파싱 또는 필드 검증 실패 |
| `INTERNAL_ERROR` | X | 분류되지 않은 내부 오류 |

AI 처리는 저장 요청과 분리된 비동기 작업에서 호출한다. 이미지 AI 실패가 저장 API의 201 응답을 지연시키면 안 된다.
