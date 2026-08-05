# 우주인 AI 서버 구조 변경 보고서

- **작성일**: 2026-08-05
- **대상 브랜치**: `feature/AI-server-test`
- **핵심 변경**: 단계별 호출형 AI(`ai-mix`) → **증분 카테고리(앵커) 엔진**을 얹은 stateless 상태 전이 AI(`ai-test`)
- **검증 방식**: 실사용(실제 아이템 32건 인제스트) + 스모크 5시나리오

---

## 1. 개요

기존 AI 서버(`ai/ai-mix`)는 제목·요약 생성, 카테고리 분류, 임베딩, 3차원 좌표 축소를
각각 독립 호출하는 **단계별 stateless API**였다. 이번 변경은 여기에 **증분 카테고리 엔진**
(`POST /api/category-engine/decide`)을 추가해, 아이템이 쌓일수록 워크스페이스가 스스로
"세부 주제 카테고리"를 발견·승격하도록 만든 것이 핵심이다.

설계의 중심 원칙은 **"AI는 판단만, 상태는 백엔드가 소유"** 다. AI 서버는 어떤 워크스페이스
상태도 저장하지 않고, 백엔드가 현재 상태 + 신규 아이템을 넘기면 판단 결과(`actions`)만
돌려준다. DB·Redis 반영은 전적으로 백엔드가 한다.

---

## 2. Before → After

| 구분 | Before (`ai-mix`) | After (`ai-test`) |
|---|---|---|
| 성격 | 단계별 호출형 stateless | 단계별 + **상태 전이형** stateless |
| 카테고리 | 고정 시드 카테고리에 분류만 | 시드 분류 + **앵커 기반 세부 카테고리 자동 발견/승격** |
| 신규 엔드포인트 | — | `POST /api/category-engine/decide` |
| 상태 저장 | 없음 | 없음(동일) — 상태는 백엔드 DB·Redis |
| 컨테이너 | `aimix` (8002) | `aimix` 컨테이너를 **`ai/ai-test` 빌드로 대체**(8002, 상위집합) |
| 코드 | `woojuin_ai/{client,config,models,prompts,reduction,service}.py` | 위 + `category_{models,prompts,service}.py` |

`ai-test`는 `ai-mix` 골격을 복사해(`4a561c7`) 그 위에 엔진을 얹은 **상위집합**이다. 즉
제목·요약/분류/임베딩/좌표 엔드포인트를 그대로 서빙하면서 `decide` 하나가 더 붙었다.
compose는 기존 `aimix` 서비스가 `./ai/ai-test`를 빌드하도록 교체됐다(`4233a00`).

---

## 3. 핵심 설계 원칙 — Stateless AI + 백엔드 상태 소유

```
              [백엔드]                         [AI 서버 (ai-test)]
  현재 상태 수집(정식 카테고리·후보                판단만 수행
  shortlist·잠정 신호) + 신규 아이템   ──decide──▶  · 정식 분류
                                                  · 앵커 추출(ENTITY/UMBRELLA_TOPIC)
  actions를 DB·Redis에 원자적 반영     ◀─actions──  · 매칭/승격 판정
```

- AI는 **영속 ID를 절대 생성하지 않는다.** `itemId·categoryId·candidateId·signalId`는 모두
  백엔드 소유이며 요청으로 넣고 응답으로 echo만 된다. 새 후보/카테고리의 ID는 백엔드가
  insert 시점에 채번한다.
- AI가 생성하는 것은 **판단 결과**뿐이다: 앵커(name/type/aliases/confidence), `match`,
  `actions[].type`, `suggestedName`, `supportCountAfter`.
- 멱등성은 전적으로 백엔드가 보장한다(`decide:{ws}:{itemId}` 처리 키, `lock:cat-engine:{ws}:{anchor}`
  동시성 락, LINK/STORE/CREATE의 upsert·재사용 규칙).

> 이 경계 덕분에 AI 서버는 무상태로 수평 확장 가능하고, 엔진 실패가 아이템 가공을
> 되돌리지 않는다(폴백 = 기본 정식 분류만 유지).

---

## 4. 카테고리 엔진 판단 로직 (`decide`)

한 아이템이 들어오면 다음 순서로 판단한다 (`woojuin_ai/category_service.py`).

1. **정식 분류** — 항상 가장 가까운 **시드** 카테고리 1개에 배치(`LINK_FORMAL_CATEGORY`).
   승격 카테고리는 분류 대상에서 제외한다(넣으면 base로 뽑혀 base+승격이 하나로 붕괴하므로).
2. **앵커 추출** — 아이템에서 `ENTITY`(고유 대상) / `UMBRELLA_TOPIC`(포괄 주제) / `OTHER`를
   추출. 실패·저신뢰는 `OTHER`로 흡수해 200 안에서 안전하게 degrade.
3. **앵커 권위 매칭** (임베딩보다 우선):
   - **A. 승격 정식 카테고리 재사용** → `LINK_FORMAL_CATEGORY`, match `PROMOTED_FORMAL`
   - **B. 후보 shortlist 매칭** → `LINK_CANDIDATE`(+승격 조건 충족 시 `PROMOTE_CANDIDATE`), match `CANDIDATE`
   - **C. 잠정 신호 매칭(2번째 데이터)** → `CREATE_CANDIDATE`, match `SIGNAL`
4. **AI 의미검증 경로** — 앵커 무매칭/저신뢰면 임베딩만으로 전환 금지, AI가 재사용/전환 검토.
5. **매칭 없음** → `STORE_SIGNAL`로 잠정 신호 보류(첫 단발 데이터, 후보 생성 지연).

**매칭 우선순위**: `ENTITY_EXACT → ENTITY_ALIAS → EMBEDDING(백엔드 Top-K) → AI_REVIEW`

**승격 규칙**:
- `ENTITY`: **규칙 기반** — 동일 앵커 support ≥ 3 + confidence면 AI 없이 즉시 승격(순서 무관).
- `UMBRELLA_TOPIC`: **AI 검토** — 과잉 일반화 방지를 위해 승격 여부를 AI가 판단.

---

## 5. 데이터 모델 변경

### 5-1. DB — `V12__add_category_engine_tables.sql` (신규 4테이블)

기존 `categories` / `item_categories`는 건드리지 않고 엔진 메타를 격리했다.

| 테이블 | 역할 |
|---|---|
| `temporary_candidates` | 임시 후보. `support_count ≥ 3`이면 승격. status = `PENDING·READY_TO_PROMOTE·PROMOTED·MERGED·EXPIRED·REJECTED` |
| `candidate_aliases` | 후보 별칭(정규화 키). 같은 대상의 다른 표기(짱구/짱구는못말려)를 앵커 매칭에 사용 |
| `candidate_item_links` | 후보 ↔ 아이템 연결. supportCount 산출 근거이자 승격 시 재분류 대상 |
| `category_anchors` | 정식 카테고리의 앵커 메타(origin `SEED·AI_PROMOTED`). 승격 카테고리 재사용 매칭용 |

`workspace_id·item_id·category_id`는 기존 패턴대로 FK 없이 생 id 컬럼.

### 5-2. Redis — 잠정 신호 + 동시성 락

```
KEY   cat-signal:{workspaceId}:{normalizedAnchor}
VALUE { signalId, firstItemId, anchorType, normalizedAnchorName, aliases[],
        firstTitle, firstSummary }
TTL   신호 수명(약 14일) — 만료 시 자동 소멸(= EXPIRED)
```

- 첫 데이터는 여기 보류되고, 2번째 동일 앵커가 오면 신호를 `provisionalSignal`로 실어
  다시 decide → `CREATE_CANDIDATE` 후 키 삭제.
- 시퀀스 카운터 `cat-signal-seq`가 `signalId`를 발급.
- 동시성 락 `lock:cat-engine:{ws}:{anchor}`로 같은 대상 동시 유입 시 후보/신호 중복 방지.

---

## 6. 백엔드 연동

엔진은 `woojuin.category-engine.enabled=true`일 때만 등록되며, 코어 처리기(ItemProcessor)를
건드리지 않고 **이벤트로 느슨하게** 붙였다.

| 컴포넌트 | 역할 |
|---|---|
| `CategoryEngineItemListener` | `ItemDoneEvent`(DONE/PARTIAL 커밋) 후처리 훅. `AFTER_COMMIT + @Async`로 가공 스레드와 분리 |
| `CategoryEngineStateGatherer` | 현재 상태 수집(정식 카테고리·후보 shortlist) |
| `CategoryEngineSignalStore` | Redis 잠정 신호 조회/저장/삭제 |
| `CategoryEngineClient` | AI `decide` HTTP 호출 |
| `CategoryEngineOrchestrator` | 상태조회 → decide → (필요 시 신호 실어 2차 decide) → apply |
| `CategoryEngineActionExecutor` | actions를 **짧은 트랜잭션**으로 DB 반영 |
| `CategoryEngineController` | 연동 검증용 테스트 엔드포인트 |

**흐름**: 아이템 가공 완료 → `ItemDoneEvent` → 리스너 → 오케스트레이터가 상태 모아 decide →
`match == NONE`이고 같은 앵커의 대기 신호가 있으면 2번째 데이터로 보고 신호를 실어 재판단 →
실행기가 actions 적용.

**트랜잭션 경계**: `plan`(LLM 호출 + 짧은 읽기)은 트랜잭션 **밖**에서 돌려 느린 외부
호출이 DB 커넥션을 점유하지 않게 하고, `apply`만 자체 짧은 트랜잭션으로 반영한다.

**폴백**: decide 실패 시 `applied=false` — 엔진 actions는 하나도 적용하지 않고 아이템은
기본 정식 분류만 유지. 엔진 후처리 실패가 이미 DONE 확정된 아이템을 되돌리지 않는다.

---

## 7. 액션 종류와 적용 순서

| action | 필수 필드 | 의미 |
|---|---|---|
| `LINK_FORMAL_CATEGORY` | `categoryId` | 아이템 ↔ 정식 카테고리 연결(기본/승격) |
| `STORE_SIGNAL` | `normalizedAnchorName·anchorType·suggestedName·linkItemIds` | 첫 데이터 잠정 신호 보류 |
| `CREATE_CANDIDATE` | `suggestedName·anchorType·normalizedAnchorName·linkItemIds·supportCountAfter(=2)` | 신호 → 후보 전환(2건 연결) |
| `LINK_CANDIDATE` | `candidateId·supportCountAfter` | 기존 후보에 연결 |
| `PROMOTE_CANDIDATE` | `candidateId·categoryName·anchorType` | 후보 승격(새 정식 카테고리 생성 + 연결 데이터 재분류) |

**적용 순서(백엔드 트랜잭션)**: `LINK_FORMAL_CATEGORY` → `CREATE_CANDIDATE` →
`LINK_CANDIDATE` → `PROMOTE_CANDIDATE` → `STORE_SIGNAL`(매칭 없을 때만 마지막).
한 응답 = `LINK_FORMAL_CATEGORY` + (전환/연결/승격 중 하나) **또는** `LINK_FORMAL_CATEGORY` + `STORE_SIGNAL`.

---

## 8. 실사용 검증 결과

### 8-1. 스모크 5시나리오 (`CategoryEngineSmokeTest`, 2026-08-05, 전부 통과)

| # | 상황 | 결과 |
|---|---|---|
| 1 | 첫 동일 대상 | `LINK_FORMAL_CATEGORY` + `STORE_SIGNAL` |
| 2 | 두 번째 + 기존 신호 | `CREATE_CANDIDATE` linkItemIds=[1,2], match `SIGNAL` |
| 3 | 세 번째 + 기존 후보 | `LINK_CANDIDATE`(support 3) + `PROMOTE_CANDIDATE`(ENTITY 규칙) |
| 4 | 승격 카테고리 존재 | `LINK_FORMAL_CATEGORY`×2(기본+승격), match `PROMOTED_FORMAL` |
| 5 | 서버 오류 | 클라이언트 예외 → 백엔드가 기본 분류만 유지 |

### 8-2. 실제 워크스페이스 스냅샷 (workspace 1, user `test1@test.com`)

실사용으로 아이템 32건을 인제스트한 결과, 엔진이 **세부 카테고리 3건을 자동 승격**했다.

| 항목 | 수치 |
|---|---|
| 아이템 | 32건 (URL 22 · IMAGE 6 · MEMO 4), 전부 임베딩 보유 |
| 정식 카테고리 | 15개 = 시드 11 + **AI 승격 3(짱구는 못말려·SSAFY·공룡)** + 수동 1(부산 여행) |
| 카테고리 앵커 | 3건 (전부 `AI_PROMOTED`, `ENTITY`) |
| 임시 후보 | 4건 — 승격 3(`PROMOTED`) + **`티라노사우루스`(`PENDING`, support 2)** |
| 후보-아이템 링크 | 11건 |
| Redis 잠정 신호 | 18건 (승격 전 raw 신호, TTL ≈14일 · `cat-signal-seq=23`) |

관찰:
- **ENTITY 규칙 승격 정상 동작** — 짱구/SSAFY/공룡이 동일 앵커 3건 도달 시 자동 승격됐다.
- **승격 임계 미달 상태 보존** — `티라노사우루스`는 support 2로 `PENDING` 유지(승격 로직 경계 확인용으로 유효).
- **신호 → 후보 전환 파이프라인 확인** — Redis에 18개 raw 신호가 대기, 그중 임계 도달분만
  DB 후보로 승격됐다.

> 스냅샷 원본 데이터: `items_test1_full.json`(아이템+카테고리+후보+캐시 신호 통합), `items_test1.json`(아이템 기본 필드).

---

## 9. 한계 및 다음 단계

- 현재는 **연동 검증 단계**라, 엔진이 켜져 있으면 기존 분류(기본 카테고리) 위에 엔진의
  대상 카테고리/후보/신호가 **더해지는** 동작이다(LINK 멱등). 정식 통합 시 기본 분류와
  승격 카테고리의 표시 우선순위 정책이 필요하다.
- `UMBRELLA_TOPIC` 승격은 AI 검토에 의존 → 프롬프트/임계 튜닝 여지.
- 임베딩 Top-K 매칭(EMBEDDING method)은 백엔드 후보 shortlist 품질에 좌우 → shortlist
  구성 로직 검증 필요.
- Redis 신호 TTL 만료(EXPIRED) 시 후보화 실패 케이스에 대한 재유입 정책 정리 필요.

---

## 부록 — 관련 파일

- AI 엔진: `ai/ai-test/woojuin_ai/category_{service,models,prompts}.py`, `ai/ai-test/app.py`
- 계약 문서: `ai/ai-test/docs/category-engine-contract.md`
- DB 스키마: `backend/.../db/migration/V12__add_category_engine_tables.sql`
- 백엔드 엔진: `backend/.../domain/ai/engine/*`
- 인프라: `docker-compose.yml`(`aimix` → `./ai/ai-test` 빌드)
