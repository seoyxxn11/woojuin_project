# 집중 증분 카테고리 비교 (clustered vs interleaved)

| 순서 | 데이터 수 | 정식 수 | 재사용률 | 평균 순도 | 포착률 | 최대 파편화 | 승격 수 | 오병합 | 재분류 | 에러 |
|---|---|---|---|---|---|---|---|---|---|---|
| grouped | 30 | 7 | 0.4167 | 1.0 | 1.0 | 1 | 3 | 0 | 9 | 0 |
| interleaved | 30 | 6 | 0.3333 | 0.9792 | 0.0 | 2 | 1 | 0 | 3 | 0 |

## 순서 안정성
| goldGroupId | clustered | interleaved | 동일? |
|---|--:|--:|:--:|
| NEW_GROUP_3 | 1 | 2 | X |
| NEW_GROUP_5 | 1 | 2 | X |

- 승격 그룹 (clustered): ['NEW_GROUP_3', '장소·먹거리', '학습·커리어']
- 승격 그룹 (interleaved): ['NEW_GROUP_3']
- 승격 그룹 일치: 아니오
