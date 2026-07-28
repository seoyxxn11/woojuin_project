# 이미지 AI 입출력 계약

## 입력

- 파일 형식: JPEG, MPO, PNG, WEBP, HEIC/HEIF
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
파일 크기·해상도·토큰·처리시간 등은 벤치마크와 모니터링용 내부 정보이므로
서비스 전달용 `metadata`에는 포함하지 않는다.

## 촬영 위치 처리 흐름

```text
원본 사진 EXIF
→ 이미지 AI가 captured_at, latitude, longitude 추출
→ 백엔드 지도 어댑터가 좌표를 장소명으로 역지오코딩
→ Item에 좌표와 장소명을 저장
→ 프론트 지도뷰에 표시
```

- 이미지 AI는 EXIF에 기록된 실제 값만 전달한다.
- EXIF가 없으면 파일 생성일·OCR·시각 정보로 촬영 시각이나 좌표를 추측하지 않는다.
- `place_name`은 이미지 AI 출력이 아니라 백엔드 지도 어댑터의 역지오코딩 결과다.
- 특정 지도 SDK/API는 확정 전까지 이미지 AI에 직접 결합하지 않는다.

## 백엔드 Item 필드 책임

이미지 AI는 `title`, `description`, `tags`, `ocr_text`, `objects`, `confidence`와
원본 EXIF 메타데이터만 생성한다. 아래 값은 AI가 임의로 만들지 않는다.

| 필드 | 담당 | 초기값 또는 의미 |
| --- | --- | --- |
| `itemId` | 백엔드 | 저장 시 생성하므로 AI 단독 테스트에서는 `null` |
| `s3Key` | 백엔드 | S3 업로드 완료 후 입력 |
| `createdAt` | 백엔드 | DB 저장 시각 |
| `deletedAt` | 백엔드 | 삭제 전에는 항상 `null` |
| `url` | 백엔드 | 이미지 타입은 `null` |
| `preview` | 백엔드 | URL 미리보기용이므로 이미지 타입은 비어 있음 |
| `categories` | 텍스트 분류 단계 | 이미지 추출 직후에는 빈 배열 |
| `latitude`, `longitude` | 이미지 AI(EXIF) | GPS EXIF가 없으면 `null` |
| `captured_at` | 이미지 AI(EXIF) | 촬영시각 EXIF가 없으면 `null` |
| `place_name` | 백엔드 지도 어댑터 | 좌표가 있을 때 역지오코딩하여 생성 |

따라서 전달용 테스트 JSON의 `null`은 AI 추출 실패를 뜻하지 않는다. AI 성공 여부는
`success`, `result` 필수 필드와 `error_code`로 판단한다.

## 텍스트 카테고리 분류 연결

최신 백엔드 `AiAnalysisRequest`는 `title`, `text`, `candidateCategories`를 입력으로
받는다. 이미지 분석 성공 결과는 다음과 같이 변환한다.

```json
{
  "title": "이미지 AI가 추출한 제목",
  "text": "이미지 설명: ...\nOCR 텍스트: ...\n태그: ...\n주요 객체: ...",
  "candidateCategories": ["워크스페이스에 실제 존재하는 카테고리 이름"]
}
```

- `text`에는 설명·OCR·태그·객체를 포함해 분류 근거를 보존한다.
- OCR이 없는 일반 사진은 빈 OCR 줄을 넣지 않는다.
- 이미지 AI는 후보 카테고리를 선택하거나 새 카테고리를 만들지 않는다.
- 텍스트 분류기는 전달받은 후보 안에서만 최대 2개를 선택한다.
- 변환 함수는 `image_service.integration.build_ai_analysis_request`를 사용한다.

백엔드 `ItemResponse`는 최종 사용자 응답이며 이미지 모델의 직접 출력 형식이 아니다.
`itemId`, `status`, `s3Key`, `createdAt` 등을 이미지 AI가 임의로 채워 반환하지 않는다.

## HTTP 연결 계약

- 서버: `serve_image_ai.py`
- 상태 확인: `GET /health`
- 이미지 분석: `POST /v1/images/analyze`
- 요청: `multipart/form-data`, 파일 필드명 `file`
- 성공: HTTP 200
- 입력 오류: HTTP 400/413/422
- 일시적 모델 오류: HTTP 503
- 실패 응답도 `detail`로 감싸지 않고 아래 계약 객체를 최상위에 반환한다.

성공 응답은 기존 이미지 분석 결과에 `classificationText`를 추가한다.
백엔드 `ImageTextExtractor` 구현체는 이 값을 반환하면 된다.

```json
{
  "success": true,
  "result": {
    "title": "이미지 제목",
    "description": "이미지 설명",
    "tags": ["태그"],
    "ocr_text": "인식된 문구",
    "objects": ["객체"],
    "confidence": 0.95
  },
  "classificationText": "이미지 설명: ...\nOCR 텍스트: ...",
  "error_code": null,
  "error_message": null,
  "retryable": false,
  "metadata": {}
}
```

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
