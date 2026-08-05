# 집중 증분 카테고리 비교 (제목+요약 엔티티 모드)

| 순서 | 데이터 수 | 정식 수 | 잠정신호 | 전환 | 최대파편화 | 재사용률 | 포착률 | 승격 수 | 오병합 | 재분류 | 엔티티API실패 | AI응답실패 | 폴백에러 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| grouped | 31 | 9 | 16 | 6 | 1 | 1.0 | 1.0 | 4 | 0 | 12 | 3 | 0 | 0 |
| interleaved | 31 | 10 | 15 | 6 | 1 | 1.0 | 1.0 | 5 | 0 | 15 | 2 | 0 | 0 |

## 매칭 방법 분포 (ENTITY_EXACT / ENTITY_ALIAS / EMBEDDING / AI_REVIEW)
- grouped: AI_REVIEW:1, EMBEDDING:1, ENTITY_EXACT:13
- interleaved: EMBEDDING:1, ENTITY_EXACT:15

## 카테고리 앵커 타입 분포 (ENTITY / UMBRELLA_TOPIC / OTHER) · 규칙기반 승격
- grouped: ENTITY:11, OTHER:5, UMBRELLA_TOPIC:15 | 규칙기반 승격(ENTITY) 1 / 전체 승격 4
- interleaved: ENTITY:11, OTHER:4, UMBRELLA_TOPIC:16 | 규칙기반 승격(ENTITY) 2 / 전체 승격 5

## 그룹 내부 유사도: 제목+요약(정제) vs 제목+요약+본문(기존)
| goldGroupId | 쌍수 | 정제avg | 정제min | 정제max | 본문avg | 본문min | 본문max | avg변화 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| DIGITAL_ORGANIZATION_SERVICE | 10 | 0.369 | 0.2981 | 0.476 | 0.3823 | 0.3035 | 0.4513 | -0.0133 |
| FORTUNE_PREDICTION | 10 | 0.2907 | 0.1 | 0.4351 | 0.3076 | 0.121 | 0.3973 | -0.0169 |
| HEALTH_MENTAL | 3 | 0.3212 | 0.2547 | 0.3678 | 0.3522 | 0.2759 | 0.3929 | -0.031 |
| JJANGGU_CHARACTER | 3 | 0.2807 | 0.2485 | 0.3284 | 0.3676 | 0.2824 | 0.4257 | -0.0869 |
| JP_SURNAME | 3 | 0.2709 | 0.0658 | 0.6379 | 0.3844 | 0.1143 | 0.9161 | -0.1135 |
| PRODUCT_INFO | 1 | 0.2793 | 0.2793 | 0.2793 | 0.3177 | 0.3177 | 0.3177 | -0.0384 |
| SELF_UNDERSTANDING | 10 | 0.296 | 0.1767 | 0.4676 | 0.3426 | 0.2212 | 0.4614 | -0.0466 |
| SSAFY_REVIEW | 10 | 0.5267 | 0.3704 | 0.724 | 0.5295 | 0.3374 | 0.6548 | -0.0028 |

- 서로 다른 그룹 간 최대 유사도: 정제 0.35 / 본문 0.3589
- 최근접 데이터가 같은 그룹일 확률: 정제 0.9355 / 본문 0.9677

## 순서 안정성
| goldGroupId | clustered | interleaved | 동일? |
|---|--:|--:|:--:|
| DIGITAL_ORGANIZATION_SERVICE | 1 | 1 | O |
| FORTUNE_PREDICTION | 1 | 1 | O |
| JJANGGU_CHARACTER | 1 | 1 | O |
| JP_SURNAME | 1 | 1 | O |
| SELF_UNDERSTANDING | 1 | 1 | O |
| SSAFY_REVIEW | 1 | 1 | O |

- 승격 그룹 (clustered): ['DIGITAL_ORGANIZATION_SERVICE', 'FORTUNE_PREDICTION', 'SELF_UNDERSTANDING', 'SSAFY_REVIEW']
- 승격 그룹 (interleaved): ['DIGITAL_ORGANIZATION_SERVICE', 'FORTUNE_PREDICTION', 'JJANGGU_CHARACTER', 'SELF_UNDERSTANDING', 'SSAFY_REVIEW']
- 승격 그룹 일치: 아니오
