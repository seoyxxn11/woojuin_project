# 집중 증분 카테고리 비교 (제목+요약 엔티티 모드)

| 순서 | 데이터 수 | 정식 수 | 잠정신호 | 전환 | 최대파편화 | 재사용률 | 포착률 | 승격 수 | 오병합 | 재분류 | 엔티티API실패 | AI응답실패 | 폴백에러 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| grouped | 31 | 6 | 27 | 3 | 1 | 1.0 | 0.5 | 1 | 0 | 3 | 0 | 0 | 0 |
| interleaved | 31 | 6 | 27 | 3 | 2 | 1.0 | 0.1667 | 1 | 0 | 3 | 0 | 0 | 0 |

## 매칭 방법 분포 (ENTITY_EXACT / ENTITY_ALIAS / EMBEDDING / AI_REVIEW)
- grouped: EMBEDDING:1, ENTITY_EXACT:3
- interleaved: EMBEDDING:2, ENTITY_EXACT:2

## 그룹 내부 유사도: 제목+요약(정제) vs 제목+요약+본문(기존)
| goldGroupId | 쌍수 | 정제avg | 정제min | 정제max | 본문avg | 본문min | 본문max | avg변화 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| DIGITAL_ORGANIZATION_SERVICE | 10 | 0.369 | 0.2981 | 0.476 | 0.3825 | 0.3034 | 0.4524 | -0.0135 |
| FORTUNE_PREDICTION | 10 | 0.2907 | 0.1 | 0.4351 | 0.3077 | 0.121 | 0.3973 | -0.017 |
| HEALTH_MENTAL | 3 | 0.3219 | 0.2547 | 0.3683 | 0.3516 | 0.2759 | 0.3929 | -0.0297 |
| JJANGGU_CHARACTER | 3 | 0.2807 | 0.2485 | 0.3284 | 0.3677 | 0.2824 | 0.4257 | -0.087 |
| JP_SURNAME | 3 | 0.2709 | 0.0658 | 0.6379 | 0.3844 | 0.1146 | 0.9155 | -0.1135 |
| PRODUCT_INFO | 1 | 0.2793 | 0.2793 | 0.2793 | 0.3178 | 0.3178 | 0.3178 | -0.0385 |
| SELF_UNDERSTANDING | 10 | 0.2956 | 0.1767 | 0.4666 | 0.3426 | 0.2211 | 0.4614 | -0.047 |
| SSAFY_REVIEW | 10 | 0.5271 | 0.3704 | 0.7241 | 0.5297 | 0.3375 | 0.655 | -0.0026 |

- 서로 다른 그룹 간 최대 유사도: 정제 0.3499 / 본문 0.3584
- 최근접 데이터가 같은 그룹일 확률: 정제 0.9355 / 본문 0.9677

## 순서 안정성
| goldGroupId | clustered | interleaved | 동일? |
|---|--:|--:|:--:|
| DIGITAL_ORGANIZATION_SERVICE | 0 | 0 | O |
| FORTUNE_PREDICTION | 0 | 0 | O |
| JJANGGU_CHARACTER | 1 | 0 | X |
| JP_SURNAME | 1 | 1 | O |
| SELF_UNDERSTANDING | 0 | 0 | O |
| SSAFY_REVIEW | 1 | 2 | X |

- 승격 그룹 (clustered): ['SSAFY_REVIEW']
- 승격 그룹 (interleaved): ['SSAFY_REVIEW']
- 승격 그룹 일치: 예
