# AI 텍스트 모델 테스트 도구

현재 기본 실험은 `qwen3:8b` 하나만 사용해 분리 처리와 통합 처리, 카테고리 설명 사용 여부가 분류 정확도에 미치는 영향을 비교합니다. 실행 진입점은 `run_classification_experiment.py`입니다.

기존 Ollama·OpenAI 모델 비교 코드와 결과는 과거 모델 선정 근거를 재현할 수 있도록 보존합니다.

## 카테고리

최종 카테고리는 다음 12개입니다.

```text
생활·할 일
학습·지식
취업·커리어
여행·장소
음식·맛집
쇼핑·제품
건강·운동
문화·콘텐츠
음악
돈·재테크
아이디어·영감
기타
```

`dataset/memo/<카테고리>/*.txt`의 상위 폴더명이 메모 테스트의 정답입니다. 상세 설명과 예시는 `config/categories.json`에서 관리하며 폴더명과 정의 이름은 정확히 일치해야 합니다. 기술 구현과 개발·IT 참고 내용은 `학습·지식`, 실행 체크리스트는 `생활·할 일`, 발상과 개선 방향은 `아이디어·영감`으로 분류합니다.

## 입력 유형별 테스트

공통 실행기 `main.py`는 `dataset/test/<카테고리>/<url|image|memo>/*.txt`를 읽습니다.
상위 카테고리 폴더가 정답 라벨이며, 카테고리 설명과 예시는 기본적으로 프롬프트에 포함됩니다.
`category-only`는 각 카테고리의 적합도 `score`를 받은 뒤 `config.yaml`의 임계값
(기본 0.65) 이상을 선택하고, 서비스 결과를 최대 2개로 제한합니다. 임계값을 넘는
항목이 없지만 후보가 있으면 가장 높은 후보 하나를 유지하고, 후보 자체가 없으면
`기타`를 fallback으로 사용합니다.

```powershell
cd ai/ai-text

# URL만
.\.venv\Scripts\python.exe .\main.py --input-type url --category-only --dry-run

# 메모만
.\.venv\Scripts\python.exe .\main.py --input-type memo --category-only --dry-run

# 이미지와 URL
.\.venv\Scripts\python.exe .\main.py --input-type image url --category-only --dry-run

# 전체 유형 (기본값)
.\.venv\Scripts\python.exe .\main.py --input-type all --category-only --dry-run
```

실제 모델 테스트에서는 `--dry-run`을 제거합니다. 설명 없이 이름만 비교하려면
`--no-category-descriptions`를 추가합니다.

### 카테고리 데이터로 설명 생성

카테고리 폴더의 실제 메모를 읽어 AI가 설명과 대표 예시를 생성할 수 있습니다. 기존 `config/categories.json`은 수정하지 않고 `config/generated/` 아래에 재사용 가능한 정의와 생성 이력을 따로 저장합니다.

```powershell
cd ai/ai-text
.\.venv\Scripts\python.exe .\generate_category_descriptions.py --dry-run
.\.venv\Scripts\python.exe .\generate_category_descriptions.py
```

일부 카테고리만 만들거나 출력 파일을 직접 지정할 수도 있습니다.

```powershell
.\.venv\Scripts\python.exe .\generate_category_descriptions.py `
  --categories "학습·지식" "생활·할 일" `
  --output .\config\generated\my-category-definitions.json
```

생성된 정의를 분류 비교 실험에서 바로 사용하려면 다음처럼 지정합니다.

```powershell
.\.venv\Scripts\python.exe .\run_classification_experiment.py `
  --category-definitions .\config\generated\my-category-definitions.json
```

기존 출력 파일은 실수로 덮어쓰지 않으며, 같은 경로를 갱신하려면 `--overwrite`를 명시해야 합니다.

### 카테고리 설명 3조건 비교

동일한 원문 메모를 `AI 생성 설명`, `기존 설명`, `카테고리 이름만`의 세 조건으로 각각 분류할 수 있습니다. 기본 임계값은 `config.yaml`의 `classification.threshold`이며 현재 0.65입니다.

```powershell
cd ai/ai-text
.\.venv\Scripts\python.exe .\run_category_description_comparison.py `
  --generated-definitions .\config\generated\category-descriptions-20260722-164953.json
```

호출 수와 설정만 먼저 확인하려면 `--dry-run`을 붙입니다. 빠른 검증은 `--limit 3`, 다른 임계값은 `--threshold 0.70`, 결과 위치 지정은 `--output <폴더>`를 사용할 수 있습니다.

결과는 `results/5차 카테고리 설명 비교/<실행시각>/`에 저장합니다. `reports/comparison.md`에서 Top-1, 완화 정확도, fallback 적용 최종 정답률과 평균 시간을 한 표로 확인할 수 있습니다.

## 현재 실험: 8B 다중 카테고리 분류 비교

모델은 카테고리별 `score`(카테고리 적합도 점수)를 반환합니다. 이 값은 통계적으로 보정된 수치로 해석하지 않습니다. 원본 응답을 한 번 저장한 뒤 같은 결과에 여러 임계값을 적용하므로 임계값 수가 늘어나도 모델 호출 수는 늘어나지 않습니다. 현재 데이터의 정답은 메모당 하나이며 ID는 `config/categories.json`에서 관리합니다.

동일한 메모를 다음 네 조건으로 실행합니다. 각 조건은 데이터마다 분류 원본 응답을 한 번만 생성합니다.

| 조건 | 처리 방식 | 카테고리 설명 | 메모당 호출 수 |
|---|---|---:|---:|
| `split-with-description` | 분류 단독 | 있음 | 1 |
| `split-without-description` | 분류 단독 | 없음 | 1 |
| `integrated-with-description` | 분류·요약·정리 통합 | 있음 | 1 |
| `integrated-without-description` | 분류·요약·정리 통합 | 없음 | 1 |

먼저 모델을 호출하지 않는 실행 계획을 확인합니다.

```powershell
.\.venv\Scripts\python.exe .\run_classification_experiment.py --dry-run
```

전체 메모를 네 조건으로 한 번씩 실행합니다. 메모 78개 기준 총 312회 호출하고, 기본 임계값 5개에 대한 1,560건 평가는 추가 호출 없이 처리합니다.

```powershell
.\.venv\Scripts\python.exe .\run_classification_experiment.py
```

실제 전체 실행 전에 메모 2개로 연결과 출력 형식을 확인할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe .\run_classification_experiment.py --limit 2
```

실행을 중단한 경우 생성된 상위 결과 폴더를 지정하면 완료된 메모를 건너뛰고 이어서 실행합니다.

```powershell
.\.venv\Scripts\python.exe .\run_classification_experiment.py `
  --resume ".\results\4차 다중 카테고리 분류 비교\20260722-150000"
```

저장된 원본 결과만 다른 임계값으로 다시 평가할 수 있습니다. 이 명령은 Ollama를 호출하지 않습니다.

```powershell
.\.venv\Scripts\python.exe .\run_classification_experiment.py `
  --evaluate-only `
  --resume ".\results\4차 다중 카테고리 분류 비교\20260722-150000" `
  --thresholds 0.55 0.60 0.65 0.70
```

결과는 다음 구조로 저장됩니다.

```text
results/4차 다중 카테고리 분류 비교/<실행시각>/
├── raw/<조건>/results.jsonl
├── threshold/<조건>/<임계값>/
│   ├── evaluation-results.json
│   ├── evaluation-results.csv
│   ├── metrics.json
│   └── evaluation-metadata.json
├── reports/
│   ├── summary.md
│   ├── threshold-comparison.csv
│   └── error-analysis.md
├── json/detailed-results.json
├── csv/detailed-results.csv
└── run-metadata.json
```

주요 지표는 `Relaxed Accuracy`, `Top-1 Accuracy`, `Exact Accuracy`, `Gold Coverage`, `Over-prediction Rate` 순으로 판단합니다. 정답만 선택하면 `EXACT_CORRECT`, 정답과 추가 카테고리 하나를 선택하면 `RELAXED_CORRECT`, 추가 카테고리가 두 개 이상이면 `WRONG_OVER_PREDICTION`입니다. 서비스 최대 2개 제한은 평가를 마친 뒤에만 적용합니다.

현재 테스트 데이터에는 정답 카테고리가 하나만 존재하므로, 정답과 함께 반환된 추가 카테고리가 실제로 적합한지 완전히 검증할 수 없습니다. 따라서 추가 카테고리 1개까지 허용하는 Relaxed Accuracy는 정식 다중 라벨 정확도가 아니라 단일 정답 데이터 기반 완화 지표입니다.

## 메모 임베딩 및 UMAP 3차원 좌표

`text-embedding-3-small`로 현재 메모 78개를 임베딩한 뒤 UMAP으로 3차원 좌표를 생성합니다. 의미 있는 제목은 본문과 함께 사용하고, `텍스트-날짜` 형식의 자동 제목은 제외합니다. API는 `config.yaml`의 SSAFY GMS Base URL과 프로젝트 루트 `.env`의 `GMS_KEY`를 사용합니다.

먼저 API를 호출하지 않는 실행 계획을 확인합니다.

```powershell
.\.venv\Scripts\python.exe .\run_embedding_umap.py --dry-run
```

의존성을 설치한 뒤 전체 데이터를 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\run_embedding_umap.py
```

소량으로 형식만 확인하려면 UMAP 변환에 필요한 최소 3개 이상을 지정합니다.

```powershell
.\.venv\Scripts\python.exe .\run_embedding_umap.py --limit 5
```

실행 중단 후에는 생성된 결과 폴더를 지정해 저장된 임베딩 다음부터 이어갑니다. 메모 본문이나 모델이 변경된 캐시는 안전을 위해 재사용하지 않습니다.

```powershell
.\.venv\Scripts\python.exe .\run_embedding_umap.py `
  --resume ".\results\4차 임베딩 시각화\20260722-170000"
```

결과 구조는 다음과 같습니다.

```text
results/4차 임베딩 시각화/<실행시각>/
├── raw/
│   └── embeddings.jsonl  # 배치마다 즉시 저장되는 재개용 벡터
├── embeddings.json       # 메모 정보와 원본 임베딩 벡터
├── umap-3d.json          # x, y, z 좌표와 카테고리
├── umap-3d.csv
└── run-metadata.json     # 모델, UMAP 설정, 요청·토큰 수
```

기본값은 API 배치 크기 64, `n_neighbors=15`, `min_dist=0.1`, `metric=cosine`, `random_state=42`입니다. `--batch-size`, `--n-neighbors`, `--min-dist`, `--metric`, `--random-state`로 바꿀 수 있습니다. API 키 값은 결과나 로그에 기록하지 않습니다.

## 설치

```powershell
cd C:\Users\SSAFY\IdeaProjects\S15P11C105\ai\ai-text
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

이 PC처럼 Python 3.14만 설치되어 있으면 `py -3.14`를 사용해도 됩니다. Ollama 모델은 별도로 설치합니다.

```powershell
ollama pull qwen3:8b
```

## SSAFY GMS API 키

`.env.example`을 참고해 프로젝트 루트(`S15P11C105/.env`)에 키를 입력합니다. 실행기는 `ai/ai-text`부터 상위 폴더를 탐색해 가장 가까운 `.env`를 사용하므로 필요하면 도구 폴더에 별도 `.env`를 둘 수도 있습니다.

```dotenv
GMS_KEY=
```

- `.env` 파일은 Git에 커밋하지 않는다.
- SSAFY GMS 키는 `GMS_KEY`라는 이름으로 관리한다.
- 키 값은 코드, 로그, 오류, JSON, CSV, 보고서에 저장하지 않는다.
- 모델 이름은 `.env`가 아니라 `config/models.yaml`에서 관리한다.

기존 설정과의 호환을 위해 `GMS_KEY`가 없으면 `OPENAI_API_KEY` 값을 GMS 인증 키로 사용합니다. 새 환경에서는 `GMS_KEY` 사용을 권장합니다.

`.gitignore`에는 `.env`, `.env.local`, `*.key`가 포함되어 있습니다. `--dry-run`은 키 값을 출력하지 않고 `configured` 또는 `missing`만 표시합니다.

## 모델 설정

`config/models.yaml`에서 모델을 관리합니다.

```yaml
models:
  - id: openai-gpt-5-nano
    provider: openai
    model: gpt-5-nano
    enabled: true
    purpose: 최저 비용 API 모델의 최소 성능 확인
    inputTypes: [text]
    testModes: [category-only, summary-only, metadata-only, integrated]
```

- `id`: CLI에서 쓰는 내부 ID이며 결과 파일명에도 사용합니다.
- `provider`: `ollama` 또는 `openai`입니다.
- `model`: Provider에 실제로 전달하는 모델명입니다.
- `enabled`: `false`이면 Suite 실행에서 `SKIPPED` 처리합니다.
- `inputTypes`, `testModes`: 지원 입력과 테스트 모드입니다.

모델을 추가하거나 변경할 때 Python 코드를 수정하지 않고 설정 파일을 수정합니다. 모델명이 변경되면 `.env`가 아니라 `config/models.yaml`의 `model` 값만 바꿉니다. 모델을 잠시 제외하려면 `enabled: false`로 설정합니다.

현재 등록 모델을 확인합니다.

```powershell
.\.venv\Scripts\python.exe main.py --list-models
```

## Suite 설정

`config/model-suites.yaml`은 비교할 내부 모델 ID를 묶습니다.

```yaml
suites:
  api-basic:
    - openai-gpt-5-nano
    - openai-gpt-5-mini

  text-comparison:
    - qwen-local
    - openai-gpt-5-nano
    - openai-gpt-5-mini
```

```powershell
.\.venv\Scripts\python.exe main.py --list-suites
```

등록되지 않은 ID, 중복 ID, 비활성 모델, 현재 모드를 지원하지 않는 모델은 해당 항목만 `SKIPPED` 처리하며 나머지 모델은 계속 실행합니다. `models.yaml` 자체의 필수 필드 누락, 중복 ID, 알 수 없는 Provider 또는 모드는 실행 전에 명확한 설정 오류로 보고합니다. 설정 파일을 프로그램이 자동 수정하지는 않습니다.

## 실행 방법

먼저 Dry-run으로 요청 수와 키 설정 여부를 확인하는 것을 권장합니다. Dry-run은 Ollama와 OpenAI를 호출하지 않고 결과 폴더도 만들지 않습니다.

```powershell
.\.venv\Scripts\python.exe main.py `
  --category-only `
  --suite text-comparison `
  --limit 3 `
  --dry-run
```

단일 모델과 데이터 한 건을 실행합니다.

```powershell
.\.venv\Scripts\python.exe main.py `
  --category-only `
  --model openai-gpt-5-nano `
  --limit 1
```

Suite를 실행합니다.

```powershell
.\.venv\Scripts\python.exe main.py `
  --category-only `
  --suite text-comparison `
  --limit 3
```

여러 모드는 한 상위 폴더 아래 모드별 폴더로 저장됩니다.

```powershell
.\.venv\Scripts\python.exe main.py `
  --suite text-comparison `
  --modes category-only summary-only metadata-only integrated `
  --limit 3
```

`--all-modes`는 네 모드를 지정하는 단축 옵션입니다. `--repeat N`은 데이터 한 건당 반복 수이며 새 공통 실행기의 기본값은 API 요청 보호를 위해 1입니다. `--test-ids TEXT-001 TEXT-002`, `--limit N`, `--memo-only`, `--include-json`도 사용할 수 있습니다. API 요청은 항상 순차 실행합니다.

기존 Ollama 전용 명령도 계속 지원합니다.

```powershell
.\.venv\Scripts\python.exe run_tests.py `
  --all-modes `
  --models qwen3:4b qwen3:8b `
  --memo-only `
  --repeat 1
```

## 구조화 출력과 공정한 비교

OpenAI Provider는 공식 SDK에 SSAFY GMS Base URL을 지정하고 OpenAI 호환 Chat Completions API를 호출합니다. Chat Completions의 JSON Schema 구조화 출력을 먼저 요청하고, GMS 또는 모델이 이를 거부하면 같은 프롬프트를 일반 JSON 응답 방식으로 다시 호출한 뒤 기존 파서와 Schema 검증기를 적용합니다. 원문, 요청 여부, 적용 여부, fallback 여부와 정제된 원인을 각 결과에 기록합니다.

```text
Base URL: https://gms.ssafy.io/gmsapi/api.openai.com/v1
인증 환경변수: GMS_KEY
API 모드: chat_completions
```

두 Provider에 공통으로 다음 조건을 적용합니다.

- 동일한 데이터 순서, testId, 카테고리와 카테고리 설명
- 동일한 프롬프트와 모드별 JSON Schema
- 동일한 평가 코드와 실패 판정 기준
- 스트리밍, 외부 검색, 도구 사용 비활성화
- 동일한 `--limit`과 반복 수

OpenAI 모델에는 호환성을 위해 temperature, seed, Ollama context length를 억지로 적용하지 않습니다. 이 차이는 실행 메타데이터에 기록합니다.

## 결과 디렉터리

기존 실행 결과는 테스트 목적에 따라 다음 두 단계로 정리합니다. 날짜가 포함된 원래 실행 폴더명은 그대로 유지합니다.

```text
results/
├── 1차 통합 테스트/   # 초기 4B·8B 통합 응답 비교
├── 2차 분류 테스트/   # 분류 정확도 중심의 모드 분리·API 비교
├── 3차 분류 구조 비교/ # 8B 분리·통합 및 설명 유무 비교
├── 4차 임베딩 시각화/ # text-embedding-3-small 및 UMAP 3차원 좌표
└── 4차 다중 카테고리 분류 비교/ # 적합도 임계값 및 단일 정답 완화 평가
```

단일 모드는 다음과 같이 저장합니다.

```text
results/<시각>-category-only-text-comparison/
├── run-metadata.json
├── model-results/
│   ├── qwen-local.json
│   ├── openai-gpt-5-nano.json
│   └── openai-gpt-5-mini.json
├── raw-responses/
│   └── <model-id>/<test-id>-<반복>.json
├── evaluation-results.json
├── comparison.csv
├── failures.csv
├── confusion-matrices/
└── report.md
```

여러 모드는 다음처럼 하나의 상위 폴더 아래에 저장합니다.

```text
results/<시각>-text-comparison/
├── category-only/
├── summary-only/
├── metadata-only/
├── integrated/
├── comparison-report.md
└── comparison-summary.json
```

`--modes` 또는 `--all-modes` 실행이 모두 완료되면 상위 폴더의 종합 비교 보고서가 자동 생성됩니다. 이 단계는 저장된 결과만 집계하며 모델 API를 추가로 호출하지 않습니다.

각 요청에는 내부 모델 ID, Provider, 요청 모델명, API가 반환한 실제 모델명, 원문, 파싱 결과, 지연 시간, 토큰, 시도 횟수, 종료 사유, 요청 ID, 오류와 구조화 출력 상태를 기록합니다. 실패 응답도 삭제하지 않습니다.

## 토큰과 비용

OpenAI가 제공하는 입력·출력·전체·캐시·추론 토큰을 가능한 범위에서 기록합니다. Provider가 값을 주지 않으면 `0`이 아니라 `null` 또는 보고서의 `N/A`입니다. Ollama와 OpenAI의 토큰 측정 기준은 다를 수 있으므로 절대적으로 같은 단위라고 가정하지 마세요.

가격은 코드가 아닌 `config/model-pricing.yaml`에서 관리합니다.

```yaml
currency: USD
unit: per_1m_tokens
updatedAt: null
models:
  openai-gpt-5-nano:
    inputPrice: null
    outputPrice: null
```

입력·출력 단가가 모두 숫자로 설정된 경우에만 `토큰 수 / 1,000,000 × 단가`로 예상 비용을 계산합니다. 가격 정보가 없으면 예상 비용은 0원이 아니라 N/A이다. 프로젝트 내부 크레딧과 실제 API 비용은 같은 값으로 취급하지 않습니다.

## 오류와 재시도

다음 오류를 구분해 결과에 기록합니다.

```text
MISSING_API_KEY, AUTHENTICATION_ERROR, MODEL_NOT_FOUND,
PERMISSION_DENIED, RATE_LIMIT_ERROR, TIMEOUT, CONNECTION_ERROR,
INVALID_REQUEST, CONTENT_FILTERED, EMPTY_RESPONSE,
JSON_PARSE_ERROR, SCHEMA_ERROR, UNKNOWN_ERROR
```

Rate limit, timeout, 연결 오류와 일부 5xx만 최대 2회 지수 백오프로 재시도합니다. 인증, 권한, 모델 없음, 잘못된 요청은 재시도하지 않습니다. 한 모델이 실패해도 Suite의 다음 모델은 계속 실행합니다. 저장 전 오류 메시지에서 API 키, Authorization, Bearer 토큰을 제거합니다.

## 평가 결과 해석

- 스키마 성공률 100%는 요약과 태그의 의미 품질이 완벽하다는 뜻이 아니다.
- 정답 데이터가 없으면 의미 평가 결과는 0%가 아니라 N/A이다.
- `requiredKeywords`, `summaryPoints`, `forbiddenClaims`가 비어 있으면 해당 의미 지표는 평가하지 않습니다.
- 작은 `--limit` 결과는 연결·형식 확인에는 유용하지만 전체 성능을 대표하지 않습니다.
- 비용 대비 운영 후보는 정확도, 지연 시간, 토큰, 설정한 가격을 함께 보고 판단합니다.

## 테스트

기본 테스트는 OpenAI API를 실제 호출하지 않습니다.

```powershell
.\.venv\Scripts\python.exe -m pytest
```

실제 API 통합 테스트는 `integration`, `requires_openai_api_key` 마커로 분리되어 기본 실행에서 제외됩니다. 명시적으로 실행하려면 키와 opt-in 환경 변수를 설정합니다.

```powershell
$env:RUN_OPENAI_INTEGRATION = "1"
.\.venv\Scripts\python.exe -m pytest -o addopts="" -m "integration and requires_openai_api_key"
```

요청 비용을 더 명확하게 통제하려면 통합 테스트 대신 먼저 Dry-run을 확인한 뒤 `main.py --model openai-gpt-5-nano --limit 1`을 직접 실행하세요.
