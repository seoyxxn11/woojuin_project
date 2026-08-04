# 집중 증분 카테고리 비교 (clustered vs interleaved)

| 순서 | 데이터 수 | 정식 수 | 잠정신호 | 전환 | 기존22 후보 | 기존22 신호만 | 재사용률 | 포착률 | 승격 수 | 오병합 | 재분류 | 에러 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| grouped | 31 | 5 | 16 | 0 | 0 | 4 | 0.0 | 0.1667 | 0 | 0 | 0 | 0 |
| interleaved | 31 | 5 | 17 | 2 | 1 | 4 | 0.0 | 0.1667 | 0 | 0 | 0 | 0 |

## 순서 안정성
| goldGroupId | clustered | interleaved | 동일? |
|---|--:|--:|:--:|
| DIGITAL_ORGANIZATION_SERVICE | 4 | 3 | X |
| FORTUNE_PREDICTION | 3 | 0 | X |
| JJANGGU_CHARACTER | 0 | 0 | O |
| JP_SURNAME | 0 | 1 | X |
| SELF_UNDERSTANDING | 1 | 2 | X |
| SSAFY_REVIEW | 0 | 2 | X |

- 승격 그룹 (clustered): []
- 승격 그룹 (interleaved): []
- 승격 그룹 일치: 예
