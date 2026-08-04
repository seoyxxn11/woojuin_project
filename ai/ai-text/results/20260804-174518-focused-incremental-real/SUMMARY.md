# 증분 카테고리 서비스 — 후보 재사용 개선 & 집중 30건 실제 테스트 결과 정리

작성 기준: `results/20260804-174518-focused-incremental-real/` (실제 API 실행, 30건, grouped·interleaved)

## 1. 무엇을 했나

- 증분 카테고리 서비스 구조(정식 5개 시드 + 임시 후보 → 승격)를 유지한 채, **임시 후보
  재사용 판단 로직을 개선**하고, **실제 API로 30건만** 두 순서(grouped·interleaved)로 검증했다.
- 새 테스트 데이터는 만들지 않았고, 기존 데이터만 사용. 기존 112건 전체·그 외에는 API를 호출하지 않음.

## 2. 실제 실행한 30건

| 유형(dataType) | 개수 | itemId | 출처 |
|---|--:|---|---|
| EXISTING_FORMAL | 22 | EXIST-001~022 | 정우현 데이터셋에서 기본 5시드에 매핑되고 요약 있는 것 (생활·건강 5 / 학습·커리어 4 / 장소·먹거리 5 / 소비·금융 4 / 문화·아이디어 4) |
| NEW_GROUP_5 | 5 | NEW5-001~005 | 기존 신규 묶음 `dataset/tester/짱구/짱구/*` |
| NEW_GROUP_3 | 3 | NEW3-001~003 | 기존 신규 묶음 `dataset/tester/ssafy/ssafy/*` |

매니페스트: `dataset/tester/focused-incremental/focused30-gold.jsonl` (기존 파일은 수정 없이 경로 참조).

## 3. 실행 조건

```text
max-count 10 / max-ai-generated 5 / formal-confidence 0.65 / formal-gap 0.10 / min-support 3 / service-max 2
후보 재사용(재보정): center-similarity 0.55 / item-similarity 0.60 / ai-review-lower-bound 0.30
모델: GMS text-embedding-3-small + OpenRouter qwen/qwen3-8b
순서: grouped(기존22→신규5→신규3), interleaved(교차). 각 순서마다 상태 초기화.
```

> 재보정 이유: 직전 28건 실제 실행에서 같은 주제 데이터의 임베딩 코사인이 0.15~0.45로 관측돼,
> 초기 임계값(0.75/0.78/0.60)에서는 AI 재사용 판단이 한 번도 호출되지 않았다. 이번엔 하한을
> 낮춰 AI 재사용 경로가 실제로 작동하도록 했다(설정 파일 불변, CLI 오버라이드).

## 4. 변경한 후보 재사용 로직

정식 분류가 애매한 데이터는 신규 후보를 바로 만들지 않고 다음 순서로 처리한다.

```text
1. centerSimilarity  (새 데이터 vs 후보 대표 임베딩)
2. maxItemSimilarity (새 데이터 vs 후보 연결 개별 데이터 최대)  → 둘 중 하나 ≥ 임계값이면 재사용
3. 애매 밴드(ai-review-lower-bound 이상~임계값 미만)면 AI에 후보 목록 제공 → REUSE / CREATE
4. CREATE일 때만 이름·설명 생성 후, 기존 후보 전체와 최종 중복 확인 → 같으면 재사용
5. 그래도 없으면 신규 후보 생성
```

구현: `src/incremental_category_service.py`(엔진), `run_incremental_category_service.py`
(`RealServiceBackend.review_reuse`), 설정 `config/incremental-category.yaml`의 `category.candidate.*`.
단위 테스트 16건 통과(REUSE_EMBEDDING / REUSE_AI / REUSE_FINAL_DEDUP 동작 검증).

## 5. 결과

| 항목 | grouped | interleaved |
|---|---|---|
| 실행 데이터 수 | 30 | 30 |
| 기존 22 → FORMAL_ONLY | 21 | 20 |
| 기존 22 → 불필요 후보 | 1 (EXIST-008) | 2 (EXIST-008, EXIST-019) |
| 신규5(짱구) 후보 수 | 2 | 3 |
| 신규3(ssafy) 후보 수 | 0 | 0 |
| 후보 재사용률 | 0.25 | 0.167 |
| 승격 수 | 0 | 0 |
| 재분류 데이터 수 | 0 | 0 |
| 오병합 건수 | 0 | 0 |
| 정식 카테고리 수 (≤10) | 5 | 5 |
| API·후보 처리 오류 | 0 | 0 |

### 신규 5건(짱구) 처리 흐름 (grouped)
```text
NEW5-001 top 0.0 → 후보 생성
NEW5-002 top 1.0 → FORMAL_ONLY(문화·아이디어)   ← 후보 단계 미진입
NEW5-003 top 0.0 → 후보 생성
NEW5-004 top 1.0 → FORMAL_ONLY(문화·아이디어)   ← 후보 단계 미진입
NEW5-005 top 0.0 → centerSim 0.92로 후보 재사용(REUSE_EMBEDDING, support 2)
→ 003+005는 정상 병합됐으나 002·004가 확신 분류로 빠져 support 3 미달 → 승격 없음
```

### 신규 3건(ssafy) 처리 흐름
```text
NEW3-001·002·003 모두 top ≈ 1.0 → 학습·커리어로 확신 분류(FORMAL_ONLY)
→ 애매가 아니어서 후보 단계에 진입조차 안 함 → 후보 0, 승격 없음
```

## 6. 확인 항목 체크

| 확인 항목 | 결과 |
|---|---|
| 실제 실행 30건 정확 | ✅ (112 미호출) |
| 기존 22 정식 직행·불필요 후보 최소 | ✅ FORMAL_ONLY 20~21, 불필요 후보 1~2 |
| 신규 5건 하나 후보로 | ❌ 2~3개로 분리(일부 FORMAL_ONLY) |
| 신규 3건 하나 후보로 | ❌ 후보 0(전부 FORMAL_ONLY) |
| 승격 시점 | 승격 없음 |
| 동일 주제 여러 후보 분리 | 짱구 일부 분리(단 003+005는 재사용 병합) |
| 두 신규 그룹 잘못 병합 | ✅ 없음(오병합 0, 순도 1.0) |
| 승격 후 재분류 | 해당 없음(승격 0) |
| grouped vs interleaved 차이 | 작음(후보 1~2개 차이, 둘 다 승격 0) |
| 정식 10 초과 | ✅ 아니오(5개) |
| API·후보 오류 | ✅ 없음 |

## 7. 재사용 로직 개선 효과 (직전 실행 대비)

| 지표 | 직전(28건, 임계값 0.75/0.78/0.60) | 이번(30건, 0.55/0.60/0.30) |
|---|--:|--:|
| 후보 재사용률 | 0.077 | 0.25 / 0.167 |
| AI 재사용 판단 호출 | 0회 | 발생(임계값 밴드 진입) |
| 임베딩 재사용 사례 | 드묾 | NEW5-005가 0.92로 재사용 |
| 오병합 | 0 | 0 |

로직 자체는 개선·검증됨(재사용률 3배↑, 유사 후보 병합 동작).

## 8. 남은 문제와 진단

파편화가 목표만큼 안 줄어든 원인은 **재사용 로직이 아니라 "후보 단계 진입" 단계**에 있다.

1. **ssafy(신규 3건)**: 분류기가 학습·커리어로 확신(top ≈ 1.0) → 애매가 아니라 후보를
   만들지 않는다. 즉 분류기 관점에서 ssafy 취업 후기는 "기본 카테고리에 속하는 데이터"이며
   새 반복 주제가 아니다. 임계값을 낮춰도 후보 단계 이전에서 갈리므로 효과 없음.
2. **짱구(신규 5건)**: 같은 주제인데 정식 분류 점수가 top 0.0~1.0으로 **불안정**. 일부는
   문화·아이디어로 확신 배치, 일부는 완전 애매로 갈려 한 후보에 3건이 못 모인다. 또한
   NEW5-001은 크롤링 본문이 나무위키 푸터/캡차뿐이라 임베딩 신호가 약하다.
3. 결론: 안전 기준(오병합 0·정식 ≤10·에러 0·112 미호출)은 모두 충족. 클러스터링/승격 미달은
   선택된 묶음(짱구·ssafy)이 분류기 상 기본 카테고리에 확신 분류되거나 분류가 불안정한
   데이터이기 때문.

### 개선 방향
- 후보 단계 진입 정책: 확신 분류라도 반복 신호가 있으면 후보에 병행 연결하거나,
  `formal-confidence-threshold`/gap을 조정해 니치 주제를 애매로 유도.
- 데이터 선택: 기본 5개로 표현하기 어려운 주제(예: 운세·심리·디지털 정리 —
  `dataset/tester/focused-incremental/`의 FOCUSED-001~020)가 이 검증 목적에 더 적합.
- 빈 본문 데이터(NEW5-001) 제외 또는 재크롤링.

## 9. 결과 파일 위치

```text
results/20260804-174518-focused-incremental-real/
├── SUMMARY.md              ← 이 문서
├── run-summary.json
├── focused-comparison.{json,csv}
├── focused-comparison-report.md
└── {grouped,interleaved}/
    ├── result.json         # 설정 + 지표 + 스냅샷 + 데이터별·후보별 상세
    ├── items.csv           # itemId·inputOrder·dataType·최초 정식·top/gap·candidateAction·
    │                       #   candidateId·candidateName·center/maxItem 유사도·supportCountAfter·
    │                       #   승격·최종 정식·재분류
    ├── candidates.csv      # 후보: 상태·supportCount·연결 itemId/goldGroup·순도·승격 시점
    ├── categories.csv
    └── report.md / report.txt
```

- 직전 28건 실행(초기 임계값): `results/20260804-171345-focused-incremental-real/`
- 코드/설정: `src/incremental_category_service.py`, `run_focused_incremental.py`,
  `config/incremental-category.yaml`
