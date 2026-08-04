# 집중 증분 카테고리 비교 (clustered vs interleaved)

| 순서 | 데이터 수 | 정식 수 | 재사용률 | 평균 순도 | 포착률 | 최대 파편화 | 승격 수 | 오병합 | 재분류 | 에러 |
|---|---|---|---|---|---|---|---|---|---|---|
| grouped | 30 | 5 | 0.25 | 1.0 | 0.0 | 2 | 0 | 0 | 0 | 0 |
| interleaved | 30 | 5 | 0.1667 | 1.0 | 0.0 | 3 | 0 | 0 | 0 | 0 |

## 순서 안정성
| goldGroupId | clustered | interleaved | 동일? |
|---|--:|--:|:--:|
| NEW_GROUP_3 | 0 | 0 | O |
| NEW_GROUP_5 | 2 | 3 | X |

- 승격 그룹 (clustered): []
- 승격 그룹 (interleaved): []
- 승격 그룹 일치: 예
