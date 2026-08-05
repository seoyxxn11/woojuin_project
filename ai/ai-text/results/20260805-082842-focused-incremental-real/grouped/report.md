# 집중 증분 카테고리 실행: grouped

## 지표
- 선택 데이터 수: 31
- 최종 정식 카테고리 수: 9 (10 초과: 아니오)
- 잠정 신호: 총 16 / 전환 6 / 대기 10 / 만료 0
- 기존 22건: 후보 0 / 신호만 5 / FORMAL_ONLY 5
- 후보 재사용률: 100.00% (재사용 4/4)
- 평균 후보 순도: 1.0
- 그룹 포착률: 100.00% (포착 ['DIGITAL_ORGANIZATION_SERVICE', 'FORTUNE_PREDICTION', 'JJANGGU_CHARACTER', 'JP_SURNAME', 'SELF_UNDERSTANDING', 'SSAFY_REVIEW'])
- 최대 파편화: 1
- 승격 수: 4 / 정밀도 1.0 / 재현율 0.6667
- 재분류 데이터 수: 12
- 오병합 건수: 0 (목표 0)
- 매칭 방법: {'ENTITY_EXACT': 13, 'AI_REVIEW': 1, 'EMBEDDING': 1}
- 에러: 엔티티API 3 / AI응답 0 / 폴백 0

## 정답 그룹별 후보 파편화
| goldGroupId | 후보 수 |
|---|--:|
| DIGITAL_ORGANIZATION_SERVICE | 1 |
| FORTUNE_PREDICTION | 1 |
| JJANGGU_CHARACTER | 1 |
| JP_SURNAME | 1 |
| SELF_UNDERSTANDING | 1 |
| SSAFY_REVIEW | 1 |

## 임시 후보
| ID | 이름 | 상태 | 지지 | 순도 | 연결 그룹 |
|---|---|---|--:|--:|---|
| 1 | 운세 | PROMOTED | 3 | 1.0 | FORTUNE_PREDICTION |
| 2 | 자기 이해 | PROMOTED | 3 | 1.0 | SELF_UNDERSTANDING |
| 3 | 디지털 정리 | PROMOTED | 3 | 1.0 | DIGITAL_ORGANIZATION_SERVICE |
| 4 | 짱구 | PENDING | 2 | 1.0 | JJANGGU_CHARACTER |
| 5 | 저작물 라이선스 | PENDING | 2 | 1.0 | JP_SURNAME |
| 6 | SSAFY | PROMOTED | 3 | 1.0 | SSAFY_REVIEW |

## 승격 결과
| 후보 | 승격 시점(itemId/순번) | 승격 supportCount | 순도 | 대표 그룹 |
|---|---|--:|--:|---|
| 운세 | FOCUSED-003/3 | 3 | 1.0 | FORTUNE_PREDICTION |
| 자기 이해 | FOCUSED-008/8 | 3 | 1.0 | SELF_UNDERSTANDING |
| 디지털 정리 | FOCUSED-013/13 | 3 | 1.0 | DIGITAL_ORGANIZATION_SERVICE |
| SSAFY | SSAFY-003/29 | 3 | 1.0 | SSAFY_REVIEW |
