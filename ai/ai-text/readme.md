# AI 텍스트 모델 테스트 도구

동일한 데이터, 프롬프트, JSON Schema, 평가 코드로 Ollama 로컬 모델과 OpenAI API 모델을 비교하는 도구입니다. 기존 Ollama 전용 진입점인 `run_tests.py`는 그대로 유지하고, 설정 기반 공통 실행은 `main.py`를 사용합니다.

지원 모드는 다음 네 가지입니다.

| 모드 | 모델 출력 | 주요 평가 |
|---|---|---|
| `category-only` | `category`, `confidence` | Accuracy, Macro Precision/Recall/F1, 혼동 행렬, confidence |
| `summary-only` | `summary` | 필수 키워드·핵심 내용 재현율, 금지 표현 |
| `metadata-only` | `tags`, `keywords` | 개수·중복 제약, 원문 키워드 포함 비율 |
| `integrated` | 요약, 카테고리, 태그, 키워드 | 분류·요약·메타데이터 통합 평가 |

## 카테고리

최종 카테고리는 다음 11개입니다.

```text
생활·할 일
학습·지식
취업·커리어
여행·장소
음식·맛집
쇼핑·제품
건강·운동
문화·콘텐츠
돈·재테크
아이디어·영감
기타
```

`dataset/memo/<카테고리>/*.txt`의 상위 폴더명이 메모 테스트의 정답입니다. 상세 설명과 예시는 `config/categories.json`에서 관리하며 폴더명과 정의 이름은 정확히 일치해야 합니다. 기술 구현과 개발·IT 참고 내용은 `학습·지식`, 실행 체크리스트는 `생활·할 일`, 발상과 개선 방향은 `아이디어·영감`으로 분류합니다.

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
└── 2차 분류 테스트/   # 분류 정확도 중심의 모드 분리·API 비교
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
