# 집중 증분 카테고리 실행: interleaved

## 지표
- 선택 데이터 수: 31
- 최종 정식 카테고리 수: 6 (10 초과: 아니오)
- 잠정 신호: 총 27 / 전환 3 / 대기 24 / 만료 0
- 기존 22건: 후보 0 / 신호만 5 / FORMAL_ONLY 5
- 후보 재사용률: 100.00% (재사용 1/1)
- 평균 후보 순도: 1.0
- 그룹 포착률: 16.67% (포착 ['JP_SURNAME'])
- 최대 파편화: 2
- 승격 수: 1 / 정밀도 1.0 / 재현율 0.1667
- 재분류 데이터 수: 3
- 오병합 건수: 0 (목표 0)
- 매칭 방법: {'ENTITY_EXACT': 2, 'EMBEDDING': 2}
- 에러: 엔티티API 0 / AI응답 0 / 폴백 0

## 정답 그룹별 후보 파편화
| goldGroupId | 후보 수 |
|---|--:|
| DIGITAL_ORGANIZATION_SERVICE | 0 |
| FORTUNE_PREDICTION | 0 |
| JJANGGU_CHARACTER | 0 |
| JP_SURNAME | 1 |
| SELF_UNDERSTANDING | 0 |
| SSAFY_REVIEW | 2 |

## 임시 후보
| ID | 이름 | 상태 | 지지 | 순도 | 연결 그룹 |
|---|---|---|--:|--:|---|
| 1 | SSAFY | PROMOTED | 3 | 1.0 | SSAFY_REVIEW |
| 2 | 라이선스 정보 | PENDING | 2 | 1.0 | JP_SURNAME |
| 3 | 삼성 청년 SW·AI 아카데미 | PENDING | 2 | 1.0 | SSAFY_REVIEW |

## 승격 결과
| 후보 | 승격 시점(itemId/순번) | 승격 supportCount | 순도 | 대표 그룹 |
|---|---|--:|--:|---|
| SSAFY | SSAFY-003/23 | 3 | 1.0 | SSAFY_REVIEW |
