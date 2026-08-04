# 후보 진입 정책 개선 — 30건 실제 테스트 결과 정리

> ⚠️ **실험 기준점(baseline), 최종 정책 아님.** 이 버전은 "첫 데이터에서 바로 후보 CREATE"
> 정책이며, 기존 22건 중 19건이 불필요 후보를 만드는 **과생성**이 확인됐다. 다음 단계로
> 생성 지연(deferred creation) 정책을 적용해 과생성을 개선한다. 이 결과는 그 비교 기준점이다.


기준: `results/20260804-195515-focused-incremental-real/` (실제 API, 30건, grouped·interleaved)
직전(진입 정책 개선 전): `results/20260804-174518-focused-incremental-real/`

## 1. 변경한 후보 진입 정책

- 이전: 정식 분류 점수가 높으면(FORMAL_ONLY) 후보 단계에 진입조차 안 함 → 같은 세부 주제가 반복돼도 누적 불가.
- 개선: **확신 분류 여부와 무관하게 항상 후보 진입을 평가**한다.
  1. 데이터는 항상 가장 가까운 정식 카테고리에 먼저 표시(승격 전까지 유지).
  2. 기존 후보와 임베딩(center 또는 maxItem)이 유사하면 → 병행 연결(REUSE).
  3. 임베딩이 애매하면 AI가 판단: **REUSE**(기존 세부주제) / **CREATE**(정식보다 구체적·반복될 세부주제) / **SKIP**(그냥 일반 데이터).
  4. SKIP이면 후보를 만들지 않고 정식 카테고리에만 유지.
  5. 후보 3건 이상 → 일관성 검토 후 승격, 연결 데이터 재분류(기존과 동일).

또한 본문이 캡차·푸터뿐이던 **NEW5-001을 같은 그룹(짱구 등장인물)의 정상 데이터로 교체**했다.

## 2. 실행 데이터 (정확히 30건, 112 미호출)
기존 22(EXIST-001~022) + 신규 5묶음(NEW5-001~005, 짱구) + 신규 3묶음(NEW3-001~003, ssafy).
설정: center 0.55 / item 0.60 / ai-lower 0.30, min-support 3, 정식 ≤10, AI 승격 ≤5.

## 3. 결과

| 항목 | grouped | interleaved |
|---|---|---|
| 데이터 수 | 30 | 30 |
| 기존 22 → FORMAL_ONLY | 3 | 3 |
| 기존 22 → 불필요 후보 | **19** | **19** |
| 신규5(짱구) 후보 수 | **1** | 2 |
| 신규3(ssafy) 후보 수 | **1** | 2 |
| 후보 재사용률 | 0.417 | 0.333 |
| 승격 수 | 3 | 1 |
| 재분류 데이터 수 | 7 | 3 |
| 오병합 (NEW5↔NEW3) | **0** | **0** |
| 정식 카테고리 수 (≤10) | 8 | 6 |
| API·후보 오류 | 0 | 0 |

### 신규 3건(ssafy) — 개선 목표 달성
```
NEW3-001 (확신 분류) → 진입 CREATE 후보 생성
NEW3-002 → REUSE_EMBEDDING (support 2)
NEW3-003 → REUSE_EMBEDDING (support 3) → 승격  ✅
```
확신 분류(학습·커리어)였음에도 진입 정책 덕분에 후보로 누적되어 3건째 승격까지 도달.

### 신규 5건(짱구) — 부분 달성
```
NEW5-001 (확신) → CREATE 후보 / NEW5-004 → REUSE_AI (support 2)
NEW5-002·003·005 → SKIP (AI가 '문화·아이디어 일반 데이터'로 판단)
→ 후보 1개로 모였으나(파편화 1) support 2에 그쳐 미승격
```

### 확신 분류 후 병행 연결된 데이터
NEW5-001·004, NEW3-001 등 `formalConfident=True`인데 후보에 병행 연결됨(정책이 의도대로 작동).

## 4. 개선/부작용 요약

- ✅ 목표 달성: 확신 분류 데이터도 후보 진입 → **NEW3는 클러스터링+승격**, NEW5는 단일 후보로 수렴(파편화 1). 재사용률 0.077→0.42로 상승. 오병합 0, 정식 ≤10, 에러 0, 30건만 호출.
- ⚠️ 부작용(과생성): 기존 22건 중 **19건이 불필요 후보를 생성**. AI(qwen3-8b)가 진입 판단에서 일반 데이터를 거의 다 "구체적 세부주제"로 보고 CREATE. 목표(기존 22 대부분 FORMAL_ONLY)와 반대. 일부 기존-데이터 후보가 승격까지 됨(자동 정리 프로그램/셀프박스).

## 5. grouped vs interleaved 차이
grouped가 더 잘 뭉침(NEW5 1·NEW3 1, 승격 3) vs interleaved(NEW5 2·NEW3 2, 승격 1). 같은 그룹 데이터가 흩어져 들어오는 interleaved에서 파편화가 늘고 support 3 도달이 줄어 승격이 적음. 기존22 불필요 후보 수(19)와 오병합(0)은 두 순서 동일.

## 6. 남은 문제와 다음 단계

핵심은 **AI CREATE 게이트가 너무 느슨**하다는 것(과생성). 진입 정책 자체는 올바르게 작동.
- 권장 1: 생성 지연(defer) — 첫 확신 데이터는 바로 후보를 만들지 말고 '잠정' 표시했다가, **유사한 2번째 데이터가 올 때만 후보를 실체화**. 반복성이 실제로 확인될 때만 후보가 생겨 과생성을 크게 줄인다.
- 권장 2: 진입 프롬프트를 훨씬 엄격히(기본 SKIP, "명백히 반복되고 정식보다 구체적일 때만 CREATE") + confidence 하한 도입, 또는 더 큰 모델로 진입 판단.
- 권장 3: 기존-데이터 후보 승격 방지 — 승격 검토에 순도/반복성 조건 강화.

## 7. 결과 파일
```
results/20260804-195515-focused-incremental-real/
├── SUMMARY.md (이 문서)
├── run-summary.json / focused-comparison.{json,csv} / focused-comparison-report.md
└── {grouped,interleaved}/ result.json · items.csv(formalConfident·candidateEntryDecision·이유 포함) · candidates.csv · categories.csv · report.md/txt
```
코드: `src/incremental_category_service.py`(review_candidate_entry), `run_incremental_category_service.py`(RealServiceBackend.review_candidate_entry), `run_focused_incremental.py`.
