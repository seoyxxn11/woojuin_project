# 증분 카테고리 서비스 — 진행 상황 핸드오프 (다른 채팅에서 이어가기용)

이 문서 + `results/` 폴더만 보면 현재 상태를 파악하고 이어서 작업할 수 있도록 정리했다.
경로는 모두 `ai/ai-text/` 기준.

## 1. 시스템 개요

실제 서비스처럼 데이터를 **한 건씩** 받아 분류하는 증분 카테고리 엔진.

- **정식(FORMAL) 카테고리**: 사용자에게 노출. 기본 5개 시드로 시작, 최대 10개(AI 승격 최대 5개).
  - 시드 5개: `생활·건강 / 학습·커리어 / 장소·먹거리 / 소비·금융 / 문화·아이디어`
    (정의는 `src/dynamic_category_experiment.py`의 `PRESET_SEEDS[5]`)
- **임시 후보(TemporaryCandidate)**: 비노출. 반복되는 세부 주제를 모아 3건 이상이면 일관성 검토 후 정식 승격.
- **잠정 신호(ProvisionalSignal)**: 비노출. 확신 분류된 단발 데이터를 후보로 바로 만들지 않고 보류(생성 지연).
  유사한 2번째 데이터가 오면 후보로 전환. 상태 WAITING/CONVERTED/EXPIRED.

### 데이터 한 건 처리 흐름 (현재 = 생성 지연 정책)
```
1. 가장 가까운 정식 카테고리에 먼저 분류(항상, 승격 전까지 여기에 표시)
2. 기존 후보와 임베딩 유사(center 또는 maxItem ≥ 임계값) → 확신이어도 병행 연결(REUSE)
3. 없으면 WAITING 잠정 신호와 비교 → 유사한 2번째면 AI 검토 후 후보 전환(supportCount 2)
4. 그래도 없고 정식 분류가 확실하면 → 후보 대신 잠정 신호(WAITING) 보류  ← 생성 지연 핵심
5. 정식 분류가 애매하면 → 기존처럼 첫 데이터에서 바로 후보 생성 가능(AI CREATE/SKIP)
6. 후보 3건 이상 → 일관성 검토 후 승격, 연결 데이터 재분류
7. 신호가 일정 입력 수 미재사용 → EXPIRED
```

## 2. 핵심 파일

| 파일 | 역할 |
|---|---|
| `src/incremental_category_service.py` | 엔진. 엔티티(FormalCategory/TemporaryCandidate/ProvisionalSignal/ItemClassification), `WorkspaceCategoryEngine.submit_item`, `DeterministicBackend`(오프라인) |
| `run_incremental_category_service.py` | 112건용 러너 + `RealServiceBackend`(GMS 임베딩 + OpenRouter AI): `classify_formal`/`review_candidate_entry`/`review_signal_conversion`/`review_promotion`/`embed` |
| `run_focused_incremental.py` | **집중 테스트 러너**. 매니페스트 데이터만 로딩(112 미호출), grouped/interleaved, 지표·비교 보고서 |
| `config/incremental-category.yaml` | 임계값 설정 |
| `dataset/tester/focused-incremental/focused30-gold.jsonl` | **현재 테스트 30건 매니페스트**(gold 라벨) |
| `tests/test_incremental_category_service.py` | 엔진 단위 테스트 19건 |

### 백엔드 인터페이스(ServiceBackend, 실/오프라인 공통)
`embed(text)`, `classify_formal(item, formal_categories)→[{categoryId,score}]`,
`review_candidate_entry(item, formal_name, candidate_infos, formal_confident)→{action:REUSE|CREATE|SKIP,...}`,
`review_signal_conversion(item, signal_info)→{convert:bool, name, description,...}`,
`review_promotion(candidate, linked_items)→{promote:bool}`.
(구 `review_reuse`는 review_candidate_entry로 대체, 하위호환용으로만 남음)

## 3. 실행 방법

```powershell
cd ai\ai-text
# 계획만 확인
.\.venv\Scripts\python.exe .\run_focused_incremental.py --manifest dataset\tester\focused-incremental\focused30-gold.jsonl --dry-run
# 실제 API (현재 재보정 임계값)
.\.venv\Scripts\python.exe .\run_focused_incremental.py `
  --manifest dataset\tester\focused-incremental\focused30-gold.jsonl `
  --mode real --model openrouter-qwen3-8b `
  --center-threshold 0.55 --item-threshold 0.60 --ai-lower 0.30
# 오프라인(무API, 결정론) 스모크: --mode 생략(기본 offline)
# 테스트
.\.venv\Scripts\python.exe -m pytest tests\test_incremental_category_service.py -q
```
- 순서 기본값: `grouped`(기존22→짱구5→ssafy3) + `interleaved`(교차). 둘만 실행.
- 키: `.env`의 `GMS_KEY`, `OPENROUTER_API_KEY` 필요(실 모드). 112건 전체는 로딩·호출하지 않음.

## 4. 설정값 (config/incremental-category.yaml + CLI)

```
max-count 10 / max-ai-generated-count 5 / formal-confidence-threshold 0.65 / formal-score-gap-threshold 0.10
candidate-min-support-count 3 / service-max-categories 2
candidate.center-similarity-threshold / item-similarity-threshold / ai-review-lower-bound
candidate.signal-similarity-threshold / signal-ttl-items   (생성 지연용)
```
- **현재 실행에서 쓴 재보정값(CLI 오버라이드)**: center 0.55 / item 0.60 / ai-lower 0.30 / signal 0.55.
  이유: 실제 임베딩(text-embedding-3-small)에서 같은 주제 코사인이 0.15~0.45라 파일 기본값(0.75/0.78/0.60)은 너무 높았음.

## 5. 테스트 데이터 (30건, gold)

`focused30-gold.jsonl` — 각 행 {itemId, source(경로), dataType, goldGroupId, goldCategoryName, expectedBehavior, mustNotMergeWithGroupIds}.
- **EXISTING_FORMAL 22건**(정우현에서 5시드에 매핑·요약 있는 것): 대부분 FORMAL_ONLY 기대.
- **NEW_GROUP_5 5건 = 짱구**(`dataset/tester/짱구/짱구/*`, 단 NEW5-001은 빈 본문이라 `focused-incremental/replacements/NEW5-001.txt`로 교체). 콘텐츠가 이질적(일본 성씨 위키 + 주인공).
- **NEW_GROUP_3 3건 = ssafy**(`dataset/tester/ssafy/ssafy/*`). 취업 후기 → 학습·커리어와 의미 겹침.
- 기존 짱구/ssafy 원본 파일은 **수정 금지**(경로 참조만).

## 6. 발전 과정 (결과 → 변경 사이클)

| 단계 | 무엇을 했나 | 관측된 결과 | 다음 변경 |
|---|---|---|---|
| 0. 설계 | 정식5+후보+승격, 한 건씩, 오프라인/실API | – | 112건 실행 |
| 1 | 실API 112×3 | 같은 주제가 이름만 달라 후보 파편화, 승격 거의 0 | 후보 재사용 개선(center+maxItem+AI+최종dedup) |
| 2 | 집중 28건 실API | 실제 임베딩(0.15~0.45)이 임계값(0.75/0.78/0.60)보다 낮아 AI 재사용 미발동 | 30건 확정 + 임계값 재보정(0.55/0.60/0.30) |
| 3 | 30건 재보정 실API | ssafy는 top 1.0 확신 분류(FORMAL_ONLY)라 후보 진입조차 안 함 | 후보 진입 정책(확신도 세부주제 평가) + NEW5-001 교체 |
| 4 | 진입 정책 실API 30건 | ssafy 승격 도달했으나 AI 과생성 — 기존22 중 **19건** 불필요 후보 | 생성 지연(잠정 신호, 2번째 유사시 전환) |
| 5 | **생성 지연 실API 30건 (현재)** | 기존22 후보 **19→8/7**로 감소, 단발성 14/15는 신호로만. NEW3 승격, NEW5 미승격 | (아래 남은 문제 참조) |

## 7. 현재 상태 지표 (5단계, grouped / interleaved)

| 지표 | grouped | interleaved |
|---|--:|--:|
| 데이터 | 30 | 30 |
| 기존22 실제 후보 / 신호만 | 8 / 14 | 7 / 15 |
| 잠정 신호 총/전환/대기/만료 | 17/6/11/0 | 18/5/13/0 |
| 신규5(짱구) 후보 수 / 승격 | 2 / X | 1 / X |
| 신규3(ssafy) 후보 수 / 승격 | 2 / O | 2 / O |
| 재사용률 / 승격 / 재분류 | 0.43 / 2 / 6 | 0.60 / 2 / 6 |
| 오병합 / 정식수 / 에러 | 0 / 7 / 0 | 0 / 7 / 0 |

## 8. 결과 폴더 지도 (results/)

| 폴더 | 단계 | 내용 |
|---|---|---|
| `20260804-142319-incremental-category-offline` | 0 | 112건 오프라인 결정론 |
| `20260804-143032-incremental-category-real` | 1 | 112건 실API(파편화 관측), HANDOFF.md |
| `20260804-171345-focused-incremental-real` | 2 | 집중 28건, 초기 임계값(미발동) |
| `20260804-174518-focused-incremental-real` | 2 | 집중 30건, 초기 임계값, SUMMARY.md |
| `20260804-195515-focused-incremental-real` | 4 | 진입 정책(과생성 19), SUMMARY.md (실험 기준점) |
| `20260804-205905-focused-incremental-real` | 5 | **생성 지연(현재), SUMMARY.md — 기준점 대비 표 포함** |

각 폴더: `{grouped,interleaved}/result.json·items.csv·candidates.csv·categories.csv·report.md`,
상위 `focused-comparison-report.md`, `run-summary.json`. items.csv에 signalAction·candidateEntryDecision·유사도 포함.

## 9. 남은 문제 & 추천 다음 단계

1. **ssafy(NEW_GROUP_3)**: 학습·커리어와 임베딩이 가까워 같은 후보에 혼합(순도 0.67). "새 세부주제"로 보려면 데이터 성격 재정의 또는 전환 AI 검토를 더 엄격히.
2. **짱구(NEW_GROUP_5)**: 콘텐츠 이질적(성씨 위키+주인공) → 임베딩상 한 군집 아님 → 미승격. 동질 데이터 필요.
3. **기존22 중 8건 후보화**: 서로 유사한 기존 쌍이 2번째에서 전환된 것. 진짜 반복이면 정상이나, 정밀도 높이려면 `review_signal_conversion` 프롬프트 강화.
4. **데이터 대표성**: 짱구/ssafy는 이 검증 목적(새 반복 주제 클러스터링)에 한계. 운세/심리/디지털 정리 같은 동질·니치 데이터(이미 `dataset/tester/focused-incremental/`의 FOCUSED-001~020 존재)가 더 적합.

## 10. 제약 / 주의

- 비교 실험 시 **모델·정식 임계값·min-support·데이터를 동시에 바꾸지 말 것**(효과 분리를 위해 한 번에 하나만).
- 실 모드는 API 비용 발생 — 항상 `--dry-run`으로 데이터 수(30) 확인 후 실행.
- git 커밋 시 husky pre-commit 훅이 Node 미설치로 실패 → `--no-verify` 필요(이 저장소 로컬 환경 한정). 브랜치 `ai-test`.
- 관련 커밋 최신: `ff1343a`(지연 결과), `712543a`(러너 신호 지표), `c818826`(생성 지연 엔진).
