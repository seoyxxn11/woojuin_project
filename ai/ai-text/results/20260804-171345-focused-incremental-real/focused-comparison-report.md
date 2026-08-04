# 집중 증분 카테고리 비교 (clustered vs interleaved)

| 순서 | 데이터 수 | 정식 수 | 재사용률 | 평균 순도 | 포착률 | 최대 파편화 | 승격 수 | 오병합 | 재분류 | 에러 |
|---|---|---|---|---|---|---|---|---|---|---|
| clustered | 28 | 5 | 0.0769 | 1.0 | 0.0 | 4 | 0 | 0 | 0 | 0 |
| interleaved | 28 | 5 | 0.0667 | 1.0 | 0.0 | 4 | 0 | 0 | 0 | 0 |

## 순서 안정성
| goldGroupId | clustered | interleaved | 동일? |
|---|--:|--:|:--:|
| DIGITAL_ORGANIZATION_SERVICE | 4 | 4 | O |
| FORTUNE_PREDICTION | 2 | 3 | X |
| JJANGGU_CHARACTER | 2 | 3 | X |
| SELF_UNDERSTANDING | 3 | 3 | O |
| SSAFY_REVIEW | 0 | 0 | O |

- 승격 그룹 (clustered): []
- 승격 그룹 (interleaved): []
- 승격 그룹 일치: 예
