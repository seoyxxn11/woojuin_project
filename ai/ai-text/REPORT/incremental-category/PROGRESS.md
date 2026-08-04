# 증분 카테고리 서비스 — 진행 상황 핸드오프 (다른 채팅에서 이어가기용)

이 문서 + `results/` 폴더만 보면 현재 상태를 파악하고 이어서 작업할 수 있도록 정리했다.
경로는 모두 `ai/ai-text/` 기준.

## 0. 최신 상태 (2026-08-05, 핵심 대상=엔티티 모드) — 여기부터 읽어라

생성 지연(5단계) 이후, **핵심 대상(엔티티) 기반 매칭 + 임베딩 입력 정제(제목+요약)** 실험을 추가했다(6단계).
`use_core_entity` 설정 플래그로 격리 — 끄면 기존 동작(하위호환), 켜면 신동작.

**무엇이 바뀌었나**
- **임베딩 입력을 제목+요약만** 사용(`build_embedding_text`). 본문/excerpt 완전 제외 → 긴 본문의 세부 내용이 핵심 대상을 희석하는 문제 제거 목적.
- **핵심 대상(엔티티) 추출**: 각 데이터의 제목+요약에서 `coreEntityName / normalizedEntityName / coreEntityType(WORK|ORGANIZATION|BRAND|PERSON|TOPIC|OTHER) / aliases / entityConfidence / entityEvidence` 추출(AI). 등장인물·극장판·후기 등은 상위 작품/기관명으로 정규화(맹구·극장판·신짱구→짱구, 싸피·삼성아카데미→SSAFY).
- **매칭 우선순위** `ENTITY_EXACT → ENTITY_ALIAS → EMBEDDING → AI_REVIEW`. 이름/별칭이 일치하면 임베딩보다 우선 재사용. 생성 지연이 후보 생성을 전담(첫 데이터는 신호, 동일 엔티티 2번째면 즉시 후보 전환, 3번째 승격 검토).
- **다중 카테고리**: 기본 정식 카테고리 + 승격된 대상 카테고리(최대 2개). 승격 후 같은 엔티티 데이터는 `REUSE_PROMOTED_ENTITY`로 승격 카테고리에 2차 라벨 연결.

**최신 결과(실 API, combined 31건, `results/20260805-015344-focused-incremental-real/`)**
- 짱구: 맹구·극장판·신짱구가 `짱구`로 묶여 **grouped 승격**(순도 1.0), interleaved는 support 3 응집(AI 승격검토 보류).
- SSAFY: 취업후기 3건이 `SSAFY`로 묶여 **양쪽 승격**(순도 1.0). 이전(234000)의 학습·커리어 혼합(순도 0.67) 해소. 나무위키(004)는 `REUSE_PROMOTED_ENTITY`로 SSAFY에 재연결.
- 다중 카테고리 부여 확인: `['짱구','문화·아이디어']`, `['SSAFY','학습·커리어']`.
- 오병합 0 / 정식 6~7(≤10) / 파편화 최대 1 / 순도 1.0. 단위 테스트 26건 통과.

**7단계(카테고리 앵커, 2026-08-05 구현 완료·미실행)**
- `coreEntity`를 **`categoryAnchor`로 확장**. 추출 필드: `categoryAnchorName / categoryAnchorType(ENTITY|UMBRELLA_TOPIC|OTHER) / normalizedAnchorName / specificEntities / aliases / anchorConfidence / anchorEvidence`. 백엔드 `extract_category_anchor`(구 `extract_core_entity`는 델리게이터로 유지, 하위호환 키도 함께 반환).
- **ENTITY 타입**: 동일 정규화 앵커 3건 + confidence 충족 + 일관 → **규칙 기반 승격**(AI review_promotion 배제 → 입력 순서에 따른 승격 편차 제거). `_anchor_confident` + `_entity_consistent`로 판정.
- **UMBRELLA_TOPIC**: 과잉 일반화 위험 → 기존 **AI 승격 검토 유지**.
- 매칭 우선순위 불변(normalizedAnchorName 정확·별칭 > 임베딩). 앵커 추출 실패/저신뢰(conf<`entity_min_confidence`)면 엔티티 권위 전환(무AI) 미발동 → 임베딩 신호 전환은 **AI 의미검증(review_signal_conversion) 필수** 경로로만.
- 러너 items.csv에 `categoryAnchorType·normalizedAnchorName·specificEntities` 추가, 비교 리포트에 앵커 타입 분포·규칙기반 승격 수. 단위 테스트 **30건**(앵커 4건 포함) 통과. **아직 실 API 미실행**(임계값·모델·데이터 불변, 요청 시 실행).

**남은 사실(중요)**
- **임베딩 정제(본문 제거)만으로는 유사도가 안 올랐다**(그룹 내부 avg 소폭 하락). 실제 개선은 전부 엔티티 매칭이 가져옴.
- FORTUNE/SELF/DIGITAL은 문서마다 서로 다른 개별 엔티티(별자리≠타로≠띠별)라 엔티티로 안 묶이고, 임베딩 유사도(~0.29)도 임계값 0.55 미만 → 후보 0. (단 최근접이웃 동일그룹 확률 0.94 → 임계값 낮추면 잡힘, 이번엔 고정.)
- 순서 민감성(짱구 grouped 승격 vs interleaved 보류), 엔티티 오추출 일부(SSAFY-005→`삼성전자`).
- **아직 커밋 안 함**(코드 변경 상태). 브랜치 `ai-test`.

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
| `src/incremental_category_service.py` | 엔진. 엔티티(FormalCategory/TemporaryCandidate/ProvisionalSignal/ItemClassification), `WorkspaceCategoryEngine.submit_item`, `DeterministicBackend`(오프라인). **엔티티 모드**: `build_embedding_text`(제목+요약), `_handle_candidate_entity`, `_find_candidate_by_entity`/`_find_signal_by_entity`/`_find_promoted_formal_by_entity`, `normalize_entity_key`, `_entity_consistent` |
| `run_incremental_category_service.py` | 112건용 러너 + `RealServiceBackend`(GMS 임베딩 + OpenRouter AI): `classify_formal`/`review_candidate_entry`/`review_signal_conversion`/`review_promotion`/`embed`/**`extract_core_entity`**. `_clean_entity_name`(JSON 오염 방어) |
| `run_focused_incremental.py` | **집중 테스트 러너**. 매니페스트 데이터만 로딩(112 미호출), grouped/interleaved, 지표·비교 보고서. `--use-core-entity` 플래그, `similarity_analysis`(제목+요약 vs +본문 유사도 비교) |
| `config/incremental-category.yaml` | 임계값 설정 (엔티티 관련: `use-core-entity`, `entity-min-confidence`는 CLI/코드 기본값) |
| `dataset/tester/focused-incremental/combined-gold.jsonl` | **현재 테스트 31건 매니페스트**. FOCUSED-001~020(5니치군집) + JJANGGU_CHARACTER(3) + JP_SURNAME(3) + SSAFY_REVIEW(5) |
| `dataset/tester/focused-incremental/focused30-gold.jsonl` | (구) 30건 매니페스트 |
| `tests/test_incremental_category_service.py` | 엔진 단위 테스트 **26건**(엔티티 매칭 7건 포함) |

### 백엔드 인터페이스(ServiceBackend, 실/오프라인 공통)
`embed(text)`, `classify_formal(item, formal_categories)→[{categoryId,score}]`,
`review_candidate_entry(item, formal_name, candidate_infos, formal_confident)→{action:REUSE|CREATE|SKIP,...}`,
`review_signal_conversion(item, signal_info)→{convert:bool, name, description,...}`,
`review_promotion(candidate, linked_items)→{promote:bool}`,
**`extract_core_entity(item)→{coreEntityName, normalizedEntityName, coreEntityType, aliases, entityConfidence, entityEvidence}`**.
(구 `review_reuse`는 review_candidate_entry로 대체, 하위호환용으로만 남음)

## 3. 실행 방법

```powershell
cd ai\ai-text
# 계획만 확인
.\.venv\Scripts\python.exe .\run_focused_incremental.py --manifest dataset\tester\focused-incremental\focused30-gold.jsonl --dry-run
# 실제 API (현재 재보정 임계값)
# === 엔티티 모드 (최신, combined 31건) ===
.\.venv\Scripts\python.exe .\run_focused_incremental.py `
  --manifest dataset\tester\focused-incremental\combined-gold.jsonl `
  --use-core-entity `
  --mode real --model openrouter-qwen3-8b `
  --center-threshold 0.55 --item-threshold 0.60 --ai-lower 0.30
# --use-core-entity 빼면 기존(제목+요약+본문) 동작. --dry-run으로 31건 먼저 확인.
# 오프라인(무API, 결정론) 스모크: --mode 생략(기본 offline)
# 테스트
.\.venv\Scripts\python.exe -m pytest tests\test_incremental_category_service.py -q
```
- 순서 기본값: `grouped` + `interleaved`. 둘만 실행.
- 키: `.env`의 `GMS_KEY`, `OPENROUTER_API_KEY` 필요(실 모드). 112건 전체는 로딩·호출하지 않음.
- 엔티티 모드는 건당 **엔티티 추출 AI 호출이 추가**됨(비용 증가).

## 4. 설정값 (config/incremental-category.yaml + CLI)

```
max-count 10 / max-ai-generated-count 5 / formal-confidence-threshold 0.65 / formal-score-gap-threshold 0.10
candidate-min-support-count 3 / service-max-categories 2
candidate.center-similarity-threshold / item-similarity-threshold / ai-review-lower-bound
candidate.signal-similarity-threshold / signal-ttl-items   (생성 지연용)
```
- **현재 실행에서 쓴 재보정값(CLI 오버라이드)**: center 0.55 / item 0.60 / ai-lower 0.30 / signal 0.55.
  이유: 실제 임베딩(text-embedding-3-small)에서 같은 주제 코사인이 0.15~0.45라 파일 기본값(0.75/0.78/0.60)은 너무 높았음.

## 5. 테스트 데이터

### 현재(엔티티 모드): `combined-gold.jsonl` (31건)
각 행 {itemId, source, dataType, goldGroupId, goldCategoryName, expectedBehavior, mustNotMergeWithGroupIds}.
- **FOCUSED-001~020**(20): 동질 니치 5군집 — FORTUNE_PREDICTION(5)/SELF_UNDERSTANDING(5)/DIGITAL_ORGANIZATION_SERVICE(5)/HEALTH_MENTAL(3, FORMAL_ONLY)/PRODUCT_INFO(2, FORMAL_ONLY).
- **JJANGGU_CHARACTER**(3): 짱구 진짜 콘텐츠 = 맹구(0003)·극장판(0006)·신짱구(0007). (0000 빈페이지·0005 블로그는 제외, 0001/0002/0004 성씨는 JP_SURNAME로 분리)
- **JP_SURNAME**(3): 사토(0001)·카자마(0002)·사쿠라다(0004) — 짱구와 안 섞이는지 확인용 노이즈.
- **SSAFY_REVIEW**(5): 취업후기 3(0000~0002) + 인스타(0003) + 나무위키(0004).
- 짱구/ssafy 원본 파일 **수정 금지**(경로 참조만). 짱구/ssafy는 사용자가 새 데이터 추가하여 8개/5개로 늘린 상태.

### (구) `focused30-gold.jsonl` (30건) — 5단계까지 사용
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
| 5 | 생성 지연 실API 30건 | 기존22 후보 **19→8/7**로 감소, 단발성 14/15는 신호로만. NEW3 승격, NEW5 미승격 | 데이터 대표성 한계 → 엔티티 매칭 도입 |
| 6a | 엔티티 모드 실API combined 31건 (1차) | SSAFY 승격·순도 1.0. 짱구는 007 **JSON 파싱 오염**으로 support 2 멈춤(미승격) | 이름 필드 정제(`_clean_entity_name`) + 승격 후 재연결 |
| 6b | **엔티티 모드 (최신, 2수정 반영)** | **짱구 grouped 승격**, SSAFY 양쪽 승격, 순도 1.0, 다중카테고리 부여, 오병합 0. 임베딩 정제만으론 유사도 안 오름(개선은 엔티티가 견인) | (아래 남은 문제) |

## 7. 현재 상태 지표 (6b 엔티티 모드, combined 31건, grouped / interleaved)

| 지표 | grouped | interleaved |
|---|--:|--:|
| 데이터 | 31 | 31 |
| 승격 수 | **2 (짱구+SSAFY)** | 1 (SSAFY) |
| 후보 순도(평균) | 1.0 | 1.0 |
| 매칭방법(ENTITY_EXACT/EMBEDDING) | 5 / 1 | 5 / 1 |
| 잠정 신호 총/전환 | 25 / 3 | 25 / 3 |
| 최대 파편화 | 1 | 1 |
| 오병합 / 정식수 | 0 / 7 | 0 / 6 |
| 에러(엔티티API/AI응답/폴백) | 1 / 0 / 0 | 2 / 0 / 0 |

> 참고 5단계 지표는 git 이력/`20260804-205905` SUMMARY.md 참조.

## 8. 결과 폴더 지도 (results/)

| 폴더 | 단계 | 내용 |
|---|---|---|
| `20260804-205905-focused-incremental-real` | 5 | 생성 지연, SUMMARY.md (엔티티 도입 전 기준점) |
| `20260804-234000-focused-incremental-real` | 6전 | **제목+요약+본문**(엔티티 OFF), combined 31건. 승격 0·파편화. 비교 대조군 |
| `20260805-010804-focused-incremental-real` | 6a | 엔티티 1차. SSAFY 승격, 짱구 파싱버그로 미승격 |
| `20260805-015344-focused-incremental-real` | 6b | **엔티티 최신(2수정). 짱구 grouped 승격·SSAFY 승격·다중카테고리**. 여기를 봐라 |

각 폴더: `{grouped,interleaved}/result.json·items.csv·candidates.csv·categories.csv·report.md`,
상위 `focused-comparison-report.md`, `run-summary.json`.
items.csv(엔티티 모드): `coreEntityName·normalizedEntityName·coreEntityType·entityConfidence·matchMethod·matchedCandidateName·embeddingSimilarity·finalCategoryIds` 포함.
comparison-report.md: 매칭방법 분포 + **제목+요약 vs +본문 그룹 유사도 비교**(avg/min/max, 그룹간 최대, 최근접 동일그룹 확률).

## 9. 남은 문제 & 추천 다음 단계

1. **임베딩 정제 무효**: 본문 제거만으론 그룹 유사도가 안 올랐다(소폭 하락). 임베딩 경로 자체를 살리려면 **유사도 임계값을 실제 분포(~0.29)에 맞춰 낮추는 실험** 필요(단 그룹간 최대와 겹쳐 오병합 위험 — 최근접이웃 확률 0.94는 순위는 정확함을 시사).
2. **FORTUNE/SELF/DIGITAL 미클러스터링**: 문서마다 개별 엔티티(별자리≠타로≠띠별)라 엔티티로 안 묶임. 이들은 "주제(TOPIC) 레벨" 클러스터라, 엔티티를 더 상위 주제로 정규화하거나 임베딩 임계값 하향이 필요.
3. **순서 민감성**: 짱구가 grouped 승격 vs interleaved 보류(support 3인데 AI review_promotion이 순서에 따라 다르게 판정). 승격 검토 안정화 필요.
4. **엔티티 오추출**: SSAFY-005→`삼성전자` 등 일부 오추출. `extract_core_entity` 프롬프트/후처리 강화 여지.
5. **커밋**: 엔티티 모드 코드 변경 아직 미커밋(브랜치 `ai-test`).

## 10. 제약 / 주의

- 비교 실험 시 **모델·정식 임계값·min-support·데이터를 동시에 바꾸지 말 것**(효과 분리). 엔티티 실험도 임계값/모델 고정한 채 진행.
- 실 모드는 API 비용 발생 — 항상 `--dry-run`으로 데이터 수(31) 확인 후 실행. 엔티티 모드는 건당 엔티티 추출 호출 추가.
- git 커밋 시 husky pre-commit 훅이 Node 미설치로 실패 → `--no-verify` 필요(이 저장소 로컬 환경 한정). 브랜치 `ai-test`.
- 관련 커밋 최신: `ff1343a`(지연 결과), `712543a`(러너 신호 지표), `c818826`(생성 지연 엔진). **엔티티 모드는 아직 미커밋.**
