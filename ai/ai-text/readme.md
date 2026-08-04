# AI 텍스트 모델 테스트 도구

현재 기본 실험은 `qwen3:8b` 하나만 사용해 분리 처리와 통합 처리, 카테고리 설명 사용 여부가 분류 정확도에 미치는 영향을 비교합니다. 실행 진입점은 `run_classification_experiment.py`입니다.

기존 Ollama·OpenAI 모델 비교 코드와 결과는 과거 모델 선정 근거를 재현할 수 있도록 보존합니다.

## 로컬 AI 카테고리 검토 GUI

자동 카테고리 실험 결과를 사람이 승인하거나 직접 수정할 때 Streamlit
기반 로컬 GUI를 사용합니다.

```powershell
cd ai\ai-text
python -m pip install -r requirements.txt
python -m streamlit run review_app.py
```

### OpenRouter 병렬 실행

`.env`에 `OPENROUTER_API_KEY`를 설정한 뒤 `openrouter-qwen3-8b` 모델을 선택합니다.
`--concurrency 4`는 같은 모델에 최대 4개 요청을 동시에 보내며, 결과 파일은 입력 순서대로 저장합니다.

```powershell
python main.py `
  --model openrouter-qwen3-8b `
  --dataset-root ".\dataset\tester\정우현" `
  --input-type url `
  --category-only `
  --limit 10 `
  --repeat 1 `
  --concurrency 4
```

### 동적 카테고리 조건 테스트

`run_dynamic_category_experiments.py`는 기존 기준 테스트 코드를 보존하면서 다음
조건을 각각 또는 한 번에 실행합니다.

```text
0. baseline11               기존 11개만 사용 (기준 테스트)
1. existing11-ai            기존 11개 + 필요할 때 AI 카테고리 생성 (비누적)
2. ai-only                  기존 카테고리 없이 AI 카테고리 생성 (비누적)
3. existing3-ai             기존 3개 + AI 생성 (비누적)
4. existing5-ai             기존 5개 + AI 생성 (비누적)
5. existing7-ai             기존 7개 + AI 생성 (비누적)
6. cumulative               기존 없음 + 생성 카테고리 누적
   ai-only-cumulative       기존 없음 + AI 생성 누적
   existing3-ai-cumulative  기존 3개 + AI 생성 누적
   existing5-ai-cumulative  기존 5개 + AI 생성 누적
   existing7-ai-cumulative  기존 7개 + AI 생성 누적
   existing11-ai-cumulative 기존 11개 + AI 생성 누적
```

누적(`-cumulative`) 조건은 앞 데이터에서 생성한 카테고리를 다음 데이터의 후보로
즉시 제공합니다. 첫 번째 데이터는 후보가 없으면 반드시 새 카테고리를 만들고,
이후 데이터는 지금까지 누적된 모든 생성 카테고리와 시드 카테고리 중에서
선택하거나 새로 만듭니다. 순서 영향을 없애기 위해 누적 조건은 동시 요청 수 1로
순차 실행합니다.

그룹 별칭으로 여러 조건을 한 번에 실행할 수 있습니다.

```text
reduced-ai            기존 3개/5개/7개 (비누적) 연속 실행
reduced-ai-cumulative 기존 3개/5개/7개 누적 연속 실행
cumulative-compare    AI 전용 / 기존 5개 / 기존 7개 누적 비교 (목표 조건)
all                   기준 테스트를 포함한 기본 조건 실행
```

목표 비교(3조건)는 다음 한 줄로 실행합니다. 세 조건은 모델·데이터셋·데이터 순서·
프롬프트·응답 형식·생성 파라미터·재시도 정책을 동일하게 사용하고 초기 카테고리와
누적 여부만 다릅니다.

```powershell
python run_dynamic_category_experiments.py `
  --scenario cumulative-compare `
  --order original shuffle-42 shuffle-84 `
  --model openrouter-qwen3-8b `
  --dataset-root ".\dataset\tester\정우현" `
  --input-type url
```

#### 데이터 순서 실험

`--order`로 처리 순서를 지정합니다. 누적 결과는 처리 순서에 영향을 받으므로 각
시나리오를 여러 순서로 실행해 최종 카테고리 수와 생성 비율 변동을 비교할 수
있습니다. `shuffle-42`·`shuffle-84`는 고정 시드라 언제 실행해도 같은 순서입니다.

```text
original     기존 데이터 순서
shuffle-42   random seed 42로 섞은 순서
shuffle-84   random seed 84로 섞은 순서
all          위 세 순서 모두
```

각 시나리오와 순서 조합은 `<시나리오>_<순서>` 하위 폴더로 분리 저장합니다
(예: `existing5-ai-cumulative_shuffle-42`).

#### 누적 여부 강제 지정

시나리오 이름으로 누적 여부가 정해지지만 CLI로 덮어쓸 수 있습니다.

```powershell
--accumulate-generated-categories     # 선택한 모든 시나리오에 누적 강제 적용
--no-accumulate-generated-categories  # 누적 강제 해제 (비누적으로 실행)
```

#### 중단 후 재개

각 데이터 처리 직후 `progress.jsonl`에 결과를 추가 저장합니다. 중단된 상위
결과 폴더를 `--resume`으로 지정하면 완료된 데이터를 건너뛰고, 누적 카테고리
상태와 처리 순서를 그대로 복원해 이어서 실행합니다.

```powershell
python run_dynamic_category_experiments.py `
  --scenario cumulative-compare --order all `
  --resume ".\results\20260804-095600-dynamic-categories-openrouter-qwen3-8b"
```

인자 없이 실행하면 조건을 고르는 메뉴가 표시됩니다.

```powershell
python run_dynamic_category_experiments.py
```

목록만 확인하거나 원하는 조건 하나를 직접 실행할 수도 있습니다.

```powershell
python run_dynamic_category_experiments.py --list-scenarios

python run_dynamic_category_experiments.py `
  --scenario existing11-ai `
  --limit 10
```

3개·5개·7개 조건만 연속 실행하려면 `reduced-ai`, 기준 테스트를 포함한 기본
조건을 모두 실행하려면 `all`을 선택합니다.

```powershell
# 3개/5개/7개 + AI 생성 (비누적)
python run_dynamic_category_experiments.py `
  --scenario reduced-ai `
  --model openrouter-qwen3-8b `
  --dataset-root ".\dataset\tester\정우현" `
  --input-type url `
  --limit 10 `
  --concurrency 4
```

API를 호출하기 전에 조건, 실제 시작 카테고리, 순서 조합과 예상 요청 수를
확인하려면 `--dry-run`을 추가합니다. 누적 조건은 앞 데이터에서 생성한 카테고리를
다음 프롬프트에 넣어야 하므로 요청 순서를 보장하기 위해 동시 요청 수 1로
실행됩니다. `cumulative`(구 조건)를 기존 카테고리와 함께 시작하려면
`--cumulative-seed-count 3`, `5`, `7`, `11` 중 하나를 지정합니다.

기존 3개·5개·7개 시드는 `config/categories.json`을 자르지 않고 통합 프리셋
(`src/dynamic_category_experiment.py`의 `PRESET_SEEDS`)을 사용합니다. 5개는
`생활·건강 / 학습·커리어 / 장소·먹거리 / 소비·금융 / 문화·아이디어`, 7개는
`생활·건강 / 학습·커리어 / 여행·장소 / 음식·맛집 / 쇼핑·제품 / 돈·재테크 /
문화·아이디어`로 시작합니다.

기준 테스트는 별도로 유지된 기존 명령으로도 이전과 똑같이 실행할 수 있습니다.

```powershell
python main.py `
  --model openrouter-qwen3-8b `
  --dataset-root ".\dataset\tester\정우현" `
  --input-type url `
  --category-only `
  --limit 10 `
  --repeat 1 `
  --concurrency 4
```

#### 선택 결과 구분과 카테고리 출처

각 데이터의 선택은 다음 세 가지로 구분해 기록합니다.

```text
SEED_EXISTING       처음 제공된 시드 카테고리 선택
GENERATED_EXISTING  앞에서 AI가 생성한 카테고리 재사용
NEW_GENERATED       새로운 카테고리 생성
```

카테고리에는 최초 출처 `origin`(`SEED` 또는 `GENERATED`)과 처음 만들어진 데이터
ID `createdAtItemId`를 저장합니다. 앞에서 생성한 카테고리를 이후 데이터가 다시
선택해도 그 카테고리의 `origin`은 계속 `GENERATED`입니다. 새 이름은 누적 목록에
넣기 전에 앞뒤 공백 제거·연속 공백 축소·구분자 앞뒤 공백 정리·영문 대소문자
무시 정규화를 적용해 완전히 동일한 이름만 병합하고, 의미만 비슷한 이름은
자동으로 합치지 않고 보고서의 `duplicateCandidates`에 검토 후보로만 남깁니다.

#### 결과 저장 구조

전체 실행 결과는 하나의 상위 폴더 아래 `<시나리오>_<순서>`로 분리됩니다.

```text
results/<시각>-dynamic-categories-openrouter-qwen3-8b/
├── ai-only-cumulative_original/
│   ├── result.json          # 실행 설정 + 데이터별 결과 + 최종 카테고리
│   ├── items.csv            # itemId, inputOrder, selectionType, ...
│   ├── categories.csv       # categoryId, origin, createdAtItemId, selectedItemCount
│   ├── report.md / report.txt
│   ├── progress.jsonl       # --resume 재개용 진행 상황
│   ├── review-draft.json    # 검토 GUI가 우선 인식
│   ├── run-metadata.json / evaluation-results.json / results.csv / failures.json
│   └── raw-responses/<testId>.json
├── ai-only-cumulative_shuffle-42/
├── existing5-ai-cumulative_original/
├── ...
├── run-summary.json
├── comparison.csv           # 시나리오 × 순서 통합 비교
└── comparison-report.md     # 순서별 변동 요약 포함
```

`report.md`/`report.txt`에는 실행 정보, 선택 결과 수와 비율, 카테고리 사용 분포
(선택 데이터 수·최초 생성 데이터 ID), 1회만 사용/2회 이상 재사용 카테고리 수,
가장 많이 사용된 카테고리, 중복 검토 후보가 포함됩니다. 모든 실행이 끝나면
`comparison-report.md`가 세 조건과 데이터 순서를 한 표로 비교합니다. 검토 GUI에서는
`<시각>-dynamic-categories-...` 상위 폴더를 선택한 뒤 조건을 고르면 됩니다.
원시 응답 폴더와 실행 메타데이터 폴더는 조건 목록에서 자동으로 제외됩니다.

한 번의 테스트에서 비교한 조건을 각각 하위 폴더로 저장합니다.

```text
review-inputs/
└── WS-001/
    └── 20260803-auto-category-test/
        ├── existing-11-plus-ai/
        │   └── review-draft.json
        ├── ai-only/
        │   └── review-draft.json
        └── existing-5-plus-ai/
            └── review-draft.json
```

GUI에서 상위 결과 폴더를 고른 다음 검토할 실험 조건과 JSON을 선택합니다.
각 데이터에는 제목, AI 요약, 초기 카테고리만 표시됩니다.

- `승인하고 다음으로`: 초기 카테고리를 그대로 사용합니다.
- `거부하고 이 이름으로 변경`: 사람이 입력한 카테고리명을 최종값으로
  저장합니다. 기존 이름과 새로운 이름을 모두 사용할 수 있습니다.

검토용 JSON은 다음 형식을 권장합니다.

```json
{
  "items": [
    {
      "sourcePath": "학습·지식/0100-url.txt",
      "title": "Spring Security 정리",
      "generatedSummary": "Spring Security의 인증 흐름을 설명합니다.",
      "generatedCategory": "백엔드 개발"
    }
  ]
}
```

항목 식별자는 `itemId`, `testId`, `id`, `localId`, `sourcePath` 중 하나를
사용합니다. 생성 카테고리는 `aiCategory`, `generatedCategory`,
`category`, `parsedResponse.category` 순서로, 요약은 `summary`,
`generatedSummary`, `aiSummary`, `parsedResponse.summary` 순서로
인식합니다.

검토가 끝나면 다음 표 두 개를 화면에 표시하고 CSV와 JSON으로 받을 수
있습니다.

- 카테고리 결과표: 초기 카테고리, 초기 데이터 수, 승인·거부 수와 비율
- 데이터 상세표: 제목, 요약, 초기 카테고리, 승인·거부 결과, 거부 후
  카테고리와 최종 카테고리

검토 상태는 `review-data/WS-001/reviews/<실험 조건>/`에 자동 저장되어
브라우저를 닫아도 이어서 할 수 있습니다. 다른 저장 위치는
`WOOJUIN_REVIEW_ROOT`, 추가 탐색 위치는 `WOOJUIN_DRAFT_ROOTS`로 지정합니다.

## 증분 카테고리 서비스 (한 건씩 입력)

실제 서비스처럼 데이터가 한 번에 오지 않고 URL·이미지·메모가 **한 건씩** 저장되는
흐름을 시뮬레이션합니다. 엔진은 [src/incremental_category_service.py](src/incremental_category_service.py),
실행기는 [run_incremental_category_service.py](run_incremental_category_service.py)입니다.

- **정식(FORMAL) 카테고리**: 사용자에게 노출. 기본 5개(`생활·건강 / 학습·커리어 /
  장소·먹거리 / 소비·금융 / 문화·아이디어`)로 시작하고 **워크스페이스당 최대 10개**.
- **임시(TEMPORARY) 후보**: 사용자에게 노출하지 않는 내부 후보. 한 건만 보고 바로
  정식 카테고리를 만들지 않고, 여러 데이터에서 반복되는 주제가 확인되면 승격합니다.

### 데이터 한 건 처리 흐름

```text
1. 현재 정식 카테고리와 비교(AI 점수)
2. 최고 점수 ≥ 임계값이고 1·2위 차가 크면 → 바로 정식 분류
3. 애매하면(최고 점수 낮거나 점수 차가 작음) 기존 임시 후보와 임베딩 비교
4. 유사 후보가 있으면 해당 후보에 누적(중복 후보 생성 안 함)
5. 유사 후보가 없으면 새 임시 후보 생성
6. 데이터는 항상 가장 가까운 정식 카테고리에 우선 배치(후보는 내부 연결로만 저장)
7. 후보 연결 데이터가 min-support 이상이면 승격 검토(AI가 일관성 확인)
8. 승격되면 연결 데이터를 새 정식 카테고리로 재분류
```

정식 카테고리가 이미 10개면 후보는 계속 누적하되 승격하지 않고
`READY_TO_PROMOTE` 상태로 대기합니다. 후보 상태: `PENDING / READY_TO_PROMOTE /
PROMOTED / MERGED / EXPIRED / REJECTED`.

### 임계값 설정

임계값과 승격 조건은 코드가 아닌 [config/incremental-category.yaml](config/incremental-category.yaml)에서
조정합니다.

```yaml
category:
  max-count: 10
  max-ai-generated-count: 5
  formal-confidence-threshold: 0.65
  formal-score-gap-threshold: 0.10
  candidate-similarity-threshold: 0.80
  candidate-min-support-count: 3
```

### 실행

기본은 **API를 호출하지 않는 오프라인 결정론 모드**입니다. 112건을 `original /
shuffle-42 / shuffle-84` 세 순서로 한 건씩 입력합니다.

```powershell
cd ai\ai-text
.\.venv\Scripts\python.exe .\run_incremental_category_service.py --dry-run
.\.venv\Scripts\python.exe .\run_incremental_category_service.py
```

실제 임베딩(GMS `text-embedding-3-small`)과 AI 모델로 실행하려면 `--mode real`을
사용합니다. 정식 분류·후보 필요 판단·이름/설명 생성·승격 검토에만 AI를 호출하고,
후보 매칭 같은 유사도 비교는 임베딩으로 처리합니다.

```powershell
.\.venv\Scripts\python.exe .\run_incremental_category_service.py `
  --mode real --model openrouter-qwen3-8b --order original shuffle-42 shuffle-84
```

### 결과 저장 구조

```text
results/<시각>-incremental-category-<mode>/
├── original/  shuffle-42/  shuffle-84/
│   ├── result.json       # 설정 + 데이터별 로그 + 최종 스냅샷
│   ├── items.csv         # 데이터별: 선택 정식 카테고리·최고 점수·후보 매칭·supportCount·승격·재분류·현재 카테고리/후보 수
│   ├── categories.csv    # 정식 카테고리: id·이름·출처(SEED/PROMOTED)·최초 데이터·데이터 수
│   ├── candidates.csv    # 임시 후보: 상태·supportCount·연결 데이터·승격 카테고리
│   └── report.md / report.txt
├── run-summary.json
├── comparison.csv
└── comparison-report.md  # 순서별 최종 카테고리 수·후보 수 차이
```

> 오프라인 모드는 토큰 해시 임베딩 + 소규모 개념 확장 맵으로 흐름을 재현합니다.
> 서로 다른 표현의 의미 유사성(예: 별자리/사주/타로 → 운세)은 실제 임베딩이 더
> 정확하므로, 후보 군집 품질을 볼 때는 `--mode real`을 사용하세요.

### 후보 재사용 판단 개선

같은 주제인데 이름이 달라 후보가 파편화(운세·예측 / 운세 정보 / 운세·타로)되는 문제를
줄이기 위해, 정식 분류가 애매한 데이터는 다음 순서로 처리합니다.

```text
1. 기존 후보 대표 임베딩과의 코사인 유사도 centerSimilarity
2. 후보에 연결된 개별 데이터와의 최대 유사도 maxItemSimilarity
   → 둘 중 하나라도 임계값 이상이면 그 후보 재사용
3. 애매 밴드(ai-review-lower-bound 이상~임계값 미만)면 AI에게 재사용 여부 판단 요청
   (REUSE candidateId / CREATE)
4. CREATE일 때만 새 이름·설명 생성 후, 기존 후보 전체와 최종 중복 확인 → 같으면 재사용
5. 그래도 없으면 신규 후보 생성
```

임계값은 [config/incremental-category.yaml](config/incremental-category.yaml)의
`category.candidate` 블록으로 분리했습니다(기존 `candidate-similarity-threshold`는 하위 호환).

```yaml
category:
  candidate:
    center-similarity-threshold: 0.75
    item-similarity-threshold: 0.78
    ai-review-lower-bound: 0.60
```

### 집중(focused) 테스트

파편화·재사용을 집중 검증하는 소규모 데이터셋으로, 기존 112건을 로딩·호출하지 않고
gold 매니페스트에 명시된 데이터(현재 28건: 기존 짱구 5 + ssafy 3 + 신규 20)만 실행합니다.
실행기는 [run_focused_incremental.py](run_focused_incremental.py)입니다.

- 데이터·정답: `dataset/tester/focused-incremental/`의 신규 20건과
  `focused-gold.jsonl`(itemId·goldGroupId·goldCategoryName·expectedBehavior·mustNotMergeWithGroupIds).
  기존 짱구·ssafy 파일은 수정하지 않고 경로로만 참조합니다.
- 순서: `clustered`(같은 그룹 연속) / `interleaved`(그룹 한 건씩 교차) 두 가지만 기본 실행.

```powershell
cd ai\ai-text
.\.venv\Scripts\python.exe .\run_focused_incremental.py --dry-run
# 실제 임베딩·AI로 검증
.\.venv\Scripts\python.exe .\run_focused_incremental.py --mode real --model openrouter-qwen3-8b
```

결과는 `results/<시각>-focused-incremental-<mode>/<order>/`에 `result.json`, `items.csv`,
`candidates.csv`, `categories.csv`, `report.md/txt`로 저장하고, 상위에
`focused-comparison.{json,csv}`, `focused-comparison-report.md`를 생성합니다. 지표는
정답 그룹별 후보 파편화 수, 후보 재사용률, 후보 순도, 그룹 포착률, 승격 정밀도·재현율,
오병합 건수(목표 0), clustered/interleaved 순서 안정성입니다.

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

이미 실행한 `category-only` 결과는 모델을 다시 호출하지 않고 여러 임계값으로
재평가할 수 있습니다. 기본 비교값은 `0.55, 0.60, 0.65, 0.70, 0.75`입니다.

```powershell
.\.venv\Scripts\python.exe .\reevaluate_category_thresholds.py `
  --result-dir ".\results\20260725-213614-category-only-qwen-local"
```

값을 직접 지정하려면 `--thresholds`를 사용합니다.

```powershell
.\.venv\Scripts\python.exe .\reevaluate_category_thresholds.py `
  --result-dir ".\results\20260725-213614-category-only-qwen-local" `
  --thresholds 0.55 0.60 0.65 0.70 0.75
```

결과는 기존 실행 폴더의 `threshold-comparison` 아래에 임계값별 상세 보고서와
전체 비교 CSV, JSON, Markdown으로 저장됩니다.

URL 데이터를 `summary-only` 또는 `integrated`로 실행하면 성공한 AI 요약을 해당
`dataset/test/<카테고리>/url/*.txt` JSON의 `summary` 필드에도 기록합니다.
기록하지 않으려면 `--no-write-url-summary`를 사용합니다.

URL `category-only` 분류에서는 원문 `content`와 `preview`를 모델에 전달하지 않고
`url`과 저장된 `summary`만 사용합니다. 일부 URL의 `title`에는 게시물 원문 전체가
들어갈 수 있어 카테고리 분류 입력에서 제외합니다. 따라서 먼저 `summary-only`를 실행해
URL JSON의 `summary`를 채운 뒤 카테고리 분류를 실행하는 순서를 권장합니다.
`summary`가 비어 있거나 “요약할 내용이 없음”, “정보가 누락됨”처럼 내용 부재를
알리는 결과인 URL은 category-only 요청과 정확도 계산 분모에서 제외합니다.

실제 모델 테스트에서는 `--dry-run`을 제거합니다. 설명 없이 이름만 비교하려면
`--no-category-descriptions`를 추가합니다.

### 내보내기 TXT 구조화

각 행이 `expected`와 `result`를 가진 JSON 객체인 JSONL 형식의 TXT 파일은
다음 명령으로 카테고리별 파일로 나눌 수 있습니다.

```powershell
cd ai/ai-text
.\.venv\Scripts\python.exe .\structure_test_dataset.py "C:\Downloads\export.txt"
```

입력 파일이 `export.txt`라면 아래처럼 입력 파일명과 정답 카테고리를 기준으로
폴더를 만들고, 각 `result` 객체를 개별 TXT 파일로 저장합니다.

```text
dataset/tester/export/
├── 생활·할 일/
│   └── 0000-url.txt
└── 학습·지식/
    └── 0001-url.txt
```

여러 TXT 파일을 한 명령에 전달할 수도 있습니다. 같은 입력 파일명으로 생성된
폴더가 이미 있으면 기본적으로 중단하며, 기존 TXT를 교체하려면 `--overwrite`를
명시합니다.

구조화한 폴더를 직접 지정해 URL 요약을 생성한 뒤, 저장된 요약으로 카테고리를
분류하려면 다음 순서로 실행합니다.

```powershell
.\.venv\Scripts\python.exe .\main.py `
  --dataset-root ".\dataset\tester\<입력 파일명>" `
  --input-type url `
  --summary-only

.\.venv\Scripts\python.exe .\main.py `
  --dataset-root ".\dataset\tester\<입력 파일명>" `
  --input-type url `
  --category-only
```

첫 번째 명령은 생성된 요약을 지정 데이터셋의 각 URL TXT에 기록합니다. 두 작업을
한 명령으로 모두 실행하려면 `--modes summary-only category-only`를 사용합니다.

### 5-fold 교차검증 데이터

카테고리마다 파일을 균등하게 나눠, 각 데이터가 정확히 한 번씩 분류 평가에
사용되는 5-fold 데이터는 다음 명령으로 생성합니다.

```powershell
.\.venv\Scripts\python.exe .\create_stratified_folds.py `
  ".\dataset\tester\<입력 파일명>"
```

각 Fold의 `category-summary`는 카테고리 설명 생성용, `classification`은 분류
평가용입니다. Fold 전용 설명은 해당 폴더를 직접 지정해 생성합니다.

```powershell
.\.venv\Scripts\python.exe .\generate_category_descriptions.py `
  --dataset-root ".\dataset\tester\<입력 파일명>-5fold\fold-1\category-summary" `
  --output ".\config\generated\fold-1.json"

.\.venv\Scripts\python.exe .\main.py `
  --dataset-root ".\dataset\tester\<입력 파일명>-5fold\fold-1\classification" `
  --input-type url `
  --modes summary-only category-only `
  --category-definitions ".\config\generated\fold-1.json"
```

### 카테고리 데이터로 설명 생성

`dataset/test/<카테고리>/<memo|url|image>`의 샘플을 카테고리별로 합쳐 AI가 설명과 대표 예시를 생성할 수 있습니다. URL은 `summary`를 우선 사용하고, 없으면 `content`를 사용합니다. 둘 다 없으면 설명 생성 샘플에서 제외하며, 카테고리에 사용할 샘플이 하나도 없으면 카테고리 이름만 보고 설명을 생성합니다. 기존 `config/categories.json`은 수정하지 않고 `config/generated/` 아래에 재사용 가능한 정의와 생성 이력을 따로 저장합니다.

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
.\.venv\Scripts\python.exe .\main.py `
  --input-type url `
  --category-only `
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

## 이미지 추출 결과 → 카테고리 분류

`ai-mix`를 거치지 않고 `ai-image/results/*.jsonl`의 이미지 추출 결과를
`qwen3:8b` 카테고리 모델에 직접 전달합니다.

먼저 Ollama와 두 모델을 준비합니다.

```powershell
ollama pull qwen3-vl:8b-instruct
ollama pull qwen3:8b
ollama serve
```

프로젝트 루트에서 최신 비어 있지 않은 이미지 결과를 자동 선택해 입력만 검증합니다.

```powershell
ai\ai-text\.venv\Scripts\python.exe `
  ai\ai-text\run_image_category_test.py `
  --dry-run
```

실제 분류:

```powershell
ai\ai-text\.venv\Scripts\python.exe `
  ai\ai-text\run_image_category_test.py
```

특정 이미지 결과를 사용하려면 `--image-result`를 지정합니다.

```powershell
ai\ai-text\.venv\Scripts\python.exe `
  ai\ai-text\run_image_category_test.py `
  --image-result ai\ai-image\results\이미지결과.jsonl
```

정확도를 계산할 때는 모델 입력과 분리된 정답 JSONL을 사용합니다.
`category-answer-key.example.jsonl`을 복사해 실제 샘플 ID와 정답으로 작성합니다.

```json
{"id":"sample-001","category":"음식·맛집"}
{"id":"sample-002","category":"쇼핑·제품"}
```

```powershell
ai\ai-text\.venv\Scripts\python.exe `
  ai\ai-text\run_image_category_test.py `
  --image-result ai\ai-image\results\이미지결과.jsonl `
  --answer-key ai\ai-image\datasets\category-answer-key.jsonl
```

정답 파일은 평가에만 사용하며 이미지·텍스트 모델 프롬프트에는 전달하지 않습니다.
정답이 없으면 분류 결과는 생성하지만 정확도는 `N/A`로 표시합니다. 결과는
`ai/ai-text/results/<실행시각>-image-to-category/`의 `results.jsonl`,
`details.csv`, `report.md`에 저장됩니다.
