# Woojuin AI Mix

우주인의 제목·요약 생성, 카테고리 분류, 임베딩, 3차원 좌표 축소, 카테고리 설명
생성을 각각 독립적으로 호출할 수 있는 FastAPI 서비스입니다.

모든 생성형 AI 및 임베딩 호출은 OpenRouter를 사용하며 API 키는
`OPENROUTER_API_KEY` 환경변수에서만 읽습니다.

## 처리 흐름

각 단계는 독립 엔드포인트입니다. 앞 단계의 결과가 필요한 경우 호출자가 결과를 DB에
저장한 뒤 다음 단계의 입력으로 넘깁니다.

```text
원본(MEMO / URL / IMAGE)
  → 제목·요약 생성
  → 카테고리 분류
  → 임베딩 생성
  → 워크스페이스 전체 임베딩으로 3차원 좌표 재계산
```

카테고리 설명 생성은 위 아이템 처리 흐름과 별개로 필요할 때 호출합니다.

## 설치와 실행

Python 3.11 또는 3.12를 권장합니다.

```powershell
cd ai/ai-mix
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app:app --host 0.0.0.0 --port 8001
```

`umap-learn` 설치가 불가능한 환경에서는 `requirements-core.txt`만 설치할 수 있습니다.
이 경우 좌표 API는 요청된 UMAP 대신 PCA로 폴백하고 응답의 `warnings`에 이유를
포함합니다.

Swagger UI는 `http://localhost:8001/docs`에서 확인할 수 있습니다.

## 환경변수

| 이름 | 기본값 | 설명 |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | 없음 | 필수 API 키 |
| `OPENROUTER_CHAT_MODEL` | `qwen/qwen3-8b` | 생성·분류 모델 |
| `OPENROUTER_EMBEDDING_MODEL` | `openai/text-embedding-3-small` | 임베딩 모델 |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter API 주소 |
| `OPENROUTER_TIMEOUT_SECONDS` | `90` | 요청 제한 시간 |
| `OPENROUTER_MAX_RETRIES` | `3` | 일시 오류 재시도 횟수 |
| `CATEGORY_SCORE_THRESHOLD` | `0.65` | 카테고리 선택 임계값 |
| `CATEGORY_MAX_RESULTS` | `2` | 한 아이템의 최대 카테고리 수 |

채팅 호출은 JSON Schema 기반 Structured Outputs를 사용하고, 이를 지원하는 제공자만
선택하도록 `require_parameters`를 설정합니다.

## 공통 응답

성공 응답은 프로젝트 공통 규약을 따릅니다.

```json
{
  "status": 200,
  "message": "success",
  "data": {}
}
```

## 제목·요약 생성

### 메모

`POST /v1/title-summary/memo`

```json
{
  "title": "회의 메모",
  "text": "다음 회의까지 검색 기능 UI와 API 연동을 완료한다."
}
```

### URL

`POST /v1/title-summary/url`

```json
{
  "title": "Been By Now by Morgan Wallen on Apple Music",
  "content": null,
  "description": null,
  "thumbnailUrl": null
}
```

`thumbnailUrl`은 계약 호환을 위해 받지만 서버가 외부 이미지를 내려받거나 모델에
전달하지는 않습니다. 제목·본문·설명만 근거로 사용합니다.

### 이미지 분석 결과

`POST /v1/title-summary/image`

```json
{
  "visionTitle": "소바 국물면",
  "description": "검은 그릇에 담긴 갈색 국물의 소바 국물면이다.",
  "ocrText": null,
  "objects": ["소바", "국물", "참깨", "파"]
}
```

세 엔드포인트의 `data`는 동일합니다.

```json
{
  "title": "참깨와 파를 곁들인 소바 국물면",
  "summary": "참깨와 파 등의 고명이 올라간 일본식 소바 국물면이다."
}
```

## 카테고리 분류

`POST /v1/categories/classify`

```json
{
  "title": "참깨와 파를 곁들인 소바 국물면",
  "summary": "참깨와 파 등의 고명이 올라간 일본식 소바 국물면이다.",
  "candidateCategories": [
    {
      "categoryId": 5,
      "name": "음식·맛집",
      "description": "음식, 메뉴, 식당 방문 및 맛집 정보와 관련된 콘텐츠"
    },
    {
      "categoryId": 6,
      "name": "여행·장소",
      "description": "여행지, 명소 및 방문 장소와 관련된 콘텐츠"
    }
  ]
}
```

응답의 카테고리는 반드시 후보 목록 안의 ID와 이름만 사용합니다. 모델 결과를 받은
뒤에도 서버가 ID·이름 일치 여부, 중복, 점수 범위를 다시 검증합니다. 임계값을 넘는
후보가 없으면 분류 누락을 막기 위해 가장 높은 후보 하나를 반환하고
`fallbackUsed: true`로 표시합니다.

## 임베딩

`POST /v1/embeddings`

```json
{
  "itemId": 101,
  "title": "참깨와 파를 곁들인 소바 국물면",
  "summary": "참깨와 파 등의 고명이 올라간 일본식 소바 국물면이다.",
  "categories": [
    {
      "categoryId": 5,
      "name": "음식·맛집"
    }
  ]
}
```

실제 임베딩 문자열은 카테고리를 ID 순으로 정렬한 뒤 다음 구조로 고정합니다.

```text
카테고리: 음식·맛집
제목: 참깨와 파를 곁들인 소바 국물면
요약: 참깨와 파 등의 고명이 올라간 일본식 소바 국물면이다.
```

다건 처리가 필요하면 `POST /v1/embeddings/batch`에 `{"items": [...]}`를 보내 한
번의 OpenRouter 배치 호출로 생성할 수 있습니다.

응답에는 `embeddingModel`, `embeddingTextVersion`, `inputHash`, `dimensions`,
`embedding`이 포함됩니다. 이 메타데이터를 벡터와 함께 저장해야 입력이나 모델이 바뀐
경우에만 다시 생성할 수 있습니다.

## 3차원 좌표

`POST /v1/coordinates/reduce`

```json
{
  "method": "umap",
  "items": [
    {"itemId": 101, "embedding": [0.12, -0.03, 0.44]},
    {"itemId": 102, "embedding": [0.09, -0.01, 0.39]},
    {"itemId": 103, "embedding": [-0.21, 0.18, 0.02]}
  ],
  "nNeighbors": 15,
  "minDist": 0.1,
  "randomState": 42,
  "targetRadius": 25
}
```

- UMAP은 표본이 5개 미만이면 PCA로 폴백합니다.
- 결과는 원점 중심으로 이동한 뒤 최대 반경이 `targetRadius`가 되도록 스케일링합니다.
- `coordinateVersion`은 입력 벡터와 축소 설정의 해시입니다.
- `requestedMethod`와 실제 사용한 `method`가 모두 응답에 포함됩니다.

### 임베딩을 저장해야 하는가?

저장해야 합니다. 3차원 좌표는 원본 의미 정보를 크게 잃은 파생 데이터이므로 `x, y,
z`만으로 새 아이템을 올바르게 배치할 수 없습니다.

초기 구현의 권장 흐름은 다음과 같습니다.

1. 새 아이템의 고차원 임베딩만 OpenRouter에서 생성해 DB에 저장합니다.
2. 같은 워크스페이스의 기존 임베딩과 새 임베딩을 모두 좌표 API에 전달합니다.
3. 반환된 모든 아이템의 좌표를 `coordinateVersion` 단위로 한 트랜잭션에서 갱신합니다.
4. 같은 `inputHash + embeddingModel + embeddingTextVersion`이면 임베딩 API를 다시
   호출하지 않습니다.

데이터가 적은 현재 단계에서는 전체 재축소가 가장 단순합니다. 다만 UMAP을 매번 다시
학습하면 기존 별의 위치도 조금씩 이동할 수 있습니다. 위치 안정성이 중요해지는 시점에는
학습된 UMAP 모델을 버전별로 저장하고 새 아이템에 `transform`을 적용한 뒤, 일정 개수마다
전체 모델과 좌표를 새 버전으로 교체하는 방식으로 확장하는 것이 좋습니다.

이 서비스는 DB를 직접 읽거나 쓰지 않는 stateless 서비스입니다. 임베딩과 좌표 버전
저장은 호출하는 백엔드가 담당합니다.

## 카테고리 설명

`POST /v1/categories/description`

```json
{
  "categoryId": 5,
  "categoryName": "음식·맛집",
  "samples": [
    {
      "title": "참깨와 파를 곁들인 소바 국물면",
      "summary": "참깨와 파 등의 고명이 올라간 일본식 소바 국물면이다."
    },
    {
      "title": "성수동 생면 파스타 전문점",
      "summary": "성수동에 있는 생면 파스타 식당의 메뉴와 방문 후기다."
    }
  ]
}
```

샘플이 없으면 카테고리 이름만으로 보수적인 설명을 만듭니다. 샘플은 호출하는 쪽에서
대표 항목 10~20개를 선택하는 것을 권장하며 API는 최대 30개를 받습니다.

권장 갱신 시점은 다음과 같습니다.

- 카테고리 최초 생성
- 아이템 5개가 처음 모였을 때
- 마지막 생성 이후 아이템이 10개 추가됐을 때
- 사용자가 직접 갱신을 요청했을 때
- 저사용 시간대의 주기 작업

## 테스트

테스트는 실제 OpenRouter를 호출하지 않습니다.

```powershell
.\.venv\Scripts\python.exe -m pytest
```

실제 키로 확인하려면 서버를 실행한 뒤 Swagger UI에서 각 엔드포인트를 한 건씩
호출합니다. API 키나 전체 임베딩 벡터를 로그에 기록하지 마세요.

## 참고

- [OpenRouter Structured Outputs](https://openrouter.ai/docs/guides/features/structured-outputs)
- [OpenRouter Embeddings API](https://openrouter.ai/docs/api/reference/embeddings)
