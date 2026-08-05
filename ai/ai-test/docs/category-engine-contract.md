# 카테고리 엔진 연동 계약 (stateless decide)

실행 중인 ai-test 서버(`POST /api/category-engine/decide`)에 대한 실호출 스모크(5시나리오)로
검증한 계약이다. AI 서버는 **상태를 저장하지 않고**, 백엔드가 현재 워크스페이스 상태와 신규
아이템을 전달하면 판단만 하고 `actions`를 반환한다. DB·Redis 반영은 백엔드가 한다.

## 1. 요청 DTO

```json
{
  "workspaceId": 10,
  "item": { "itemId": 4, "type": "URL", "title": "…", "summary": "…" },
  "formalCategories": [
    { "categoryId": 2, "name": "학습·커리어", "origin": "SEED" },
    { "categoryId": 7, "name": "SSAFY", "origin": "AI_PROMOTED",
      "anchorType": "ENTITY", "normalizedAnchorName": "SSAFY", "aliases": ["싸피"] }
  ],
  "candidateShortlist": [
    { "candidateId": 7, "suggestedName": "SSAFY", "anchorType": "ENTITY",
      "normalizedAnchorName": "SSAFY", "aliases": ["싸피"], "supportCount": 2,
      "similarity": 0.6, "representativeItems": [ { "title": "…", "summary": "…" } ] }
  ],
  "provisionalSignal": {
    "signalId": 100, "firstItemId": 1, "anchorType": "ENTITY",
    "normalizedAnchorName": "SSAFY", "aliases": ["싸피"],
    "firstItem": { "title": "…", "summary": "…" }, "similarity": null
  }
}
```

- `formalCategories` = 기본 시드 + 이미 승격된 대상 카테고리.
- `candidateShortlist` / `provisionalSignal`은 백엔드가 앵커 정확일치·임베딩 Top-K로 좁혀 전달(없으면 `[]` / `null`).

## 2. 응답 DTO

```json
{
  "workspaceId": 10, "itemId": 4,
  "formalCategoryIds": [2, 7],
  "ambiguous": false,
  "categoryAnchor": { "name": "SSAFY", "normalizedName": "SSAFY", "type": "ENTITY",
                      "aliases": ["싸피"], "specificEntities": [], "confidence": 0.95 },
  "match": { "type": "PROMOTED_FORMAL", "targetId": 7, "method": "ENTITY_EXACT" },
  "actions": [ … ]
}
```

- `match.type` ∈ `PROMOTED_FORMAL | CANDIDATE | SIGNAL | NONE`
- `match.method` ∈ `ENTITY_EXACT | ENTITY_ALIAS | EMBEDDING | AI_REVIEW`

## 3. action별 필수 필드

| action | 필수 필드 | 의미 |
|---|---|---|
| `LINK_FORMAL_CATEGORY` | `categoryId` | 아이템↔정식 카테고리 연결(기본 또는 승격 대상) |
| `STORE_SIGNAL` | `normalizedAnchorName`, `anchorType`, `suggestedName`, `linkItemIds`(=[itemId]); `aliases` 선택 | 첫 데이터 잠정 신호 보류 |
| `CREATE_CANDIDATE` | `suggestedName`, `anchorType`, `normalizedAnchorName`, `linkItemIds`(=[firstItemId, itemId]), `supportCountAfter`(=2); `aliases` | 신호→후보 전환(2건 연결) |
| `LINK_CANDIDATE` | `candidateId`, `supportCountAfter` | 기존 후보에 연결 |
| `PROMOTE_CANDIDATE` | `candidateId`, `categoryName`, `anchorType` | 후보 승격(새 정식 카테고리 생성) |

## 4. action 적용 순서 (백엔드 트랜잭션)

```
1. LINK_FORMAL_CATEGORY   항상 먼저 — 기본/승격 카테고리 배치
2. CREATE_CANDIDATE       신호→후보 전환 + 원 신호(Redis) 삭제
3. LINK_CANDIDATE         후보 supportCount 갱신
4. PROMOTE_CANDIDATE      승격 = 새 정식 카테고리 생성 + 연결 데이터 재분류
5. STORE_SIGNAL           매칭 없을 때만 Redis 저장(마지막)
```

한 응답 = `LINK_FORMAL_CATEGORY` + (전환/연결/승격 중 하나) 또는 `LINK_FORMAL_CATEGORY` + `STORE_SIGNAL`.

## 5. ID 소유 구분

| 값 | 소유자 | 근거 |
|---|---|---|
| `itemId`, `categoryId`, `candidateId`, `signalId` | **백엔드** | 요청으로 넣고 응답은 그대로 echo. AI는 새 ID를 만들지 않음 |
| `categoryAnchor` (name/normalized/type/aliases/conf) | AI | 추출 결과 |
| `match`, `actions[].type`, `suggestedName`, `supportCountAfter` | AI | 판단 결과(supportCountAfter = 넘긴 support+1) |
| `CREATE_CANDIDATE`의 새 candidateId | **백엔드** | AI는 `candidateId=null` → 백엔드가 insert 시 채번 |
| `PROMOTE_CANDIDATE`의 새 정식 categoryId | **백엔드** | 승격 시 백엔드가 새 카테고리 생성·채번 |

→ AI는 영속 ID를 절대 생성하지 않는다. 백엔드 소유 ID를 참조/echo만 한다.

## 6. idempotencyKey 설계

AI가 stateless이므로 멱등성은 전적으로 백엔드가 보장한다.

- 처리 단위 키: `decide:{workspaceId}:{itemId}` — 아이템당 1회 처리(재시도·중복 이벤트 방어).
- 동시성 락(Redis): `lock:cat-engine:{workspaceId}:{normalizedAnchor}` — 같은 대상 데이터 동시 유입 시 후보/신호 중복 생성 방지.
- action 적용 멱등: LINK는 "없으면 연결", STORE_SIGNAL은 앵커 키로 upsert, CREATE_CANDIDATE는 같은 앵커 후보 존재 시 재사용.

## 7. 오류 및 폴백 규칙 (시나리오 5)

- 클라이언트는 서버 오류·타임아웃·빈/깨진 응답에 **예외를 던진다**(감지 가능).
- 백엔드 폴백: decide 실패 시 엔진 actions는 하나도 적용하지 않고, 아이템은 **기본 정식 분류만 유지**(기존 분류 폴백 또는 재처리 큐).
- decide는 원자적 판단(all-or-nothing). 트랜잭션 내 action 적용 중 DB 오류면 전체 롤백 후 재시도.
- AI 내부 개별 실패(앵커 추출 실패 등)는 서버가 흡수(OTHER/저신뢰)해 200 안에서 안전하게 degrade한다.

## 8. DB 최소 상태

```
formal_category        (기존) + origin, anchor_type, normalized_anchor_name
temporary_candidate    id, workspace_id, suggested_name, anchor_type,
                       normalized_anchor_name, support_count, status, promoted_category_id
candidate_alias        candidate_id, alias_key            (정규화 별칭, 매칭용)
candidate_item_link    candidate_id, item_id              (연결·supportCount 산출)
item_category_link     (기존) item_id, category_id        (다중 카테고리)
```

Top-K 후보 검색용 임베딩은 기존 임베딩 저장소를 재사용한다.

## 9. Redis 잠정 신호 형태

```
KEY   cat-signal:{workspaceId}:{anchorType}:{normalizedAnchor}
VALUE { signalId, firstItemId, anchorType, normalizedAnchorName,
        aliases[], firstItem:{title,summary} }
TTL   신호 수명(예: N일) — 만료 시 자동 소멸(= EXPIRED)
```

- 2번째 동일 대상 데이터가 오면 이 키로 신호를 조회해 `provisionalSignal`로 decide에 전달 →
  `CREATE_CANDIDATE` 후 키 삭제.
- 동시성 락도 Redis(6번).

## 스모크 검증 (2026-08-05)

`CategoryEngineSmokeTest`(CATEGORY_ENGINE_SMOKE=true) — 실행 중인 ai-test 서버에
`CategoryEngineClient`로 실제 호출. 5시나리오 전부 통과.

| # | 상황 | 결과 |
|---|---|---|
| 1 | 첫 동일 대상 | `LINK_FORMAL_CATEGORY` + `STORE_SIGNAL`(item[1]) |
| 2 | 두 번째 + 기존 신호 | `CREATE_CANDIDATE` linkItemIds=[1,2], match SIGNAL |
| 3 | 세 번째 + 기존 후보 | `LINK_CANDIDATE`(support 3) + `PROMOTE_CANDIDATE`(ENTITY 규칙) |
| 4 | 승격 카테고리 존재 | `LINK_FORMAL_CATEGORY`×2 (기본+승격), match PROMOTED_FORMAL |
| 5 | 서버 오류 | 클라이언트 예외 → 백엔드가 기본 분류만 유지 |
