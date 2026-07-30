# 모델 결과 비교 보고서

## 입력 결과

- C:\Users\SSAFY\IdeaProjects\S15P11C105\ai\ai-text\results\20260728-102036-qwen-local\summary-only
- C:\Users\SSAFY\IdeaProjects\S15P11C105\ai\ai-text\results\20260728-102036-qwen-local\category-only

| 모델 | 테스트 모드 | 호출 수 | 응답 성공률 | JSON 성공률 | 스키마 성공률 | 카테고리 정확도 | Macro F1 | 평균 응답 시간(ms) | P95(ms) | 평균 TPS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen-local | summary-only | 55 | 94.5% | 94.5% | 87.3% | N/A | N/A | 7891.6 | 17023.3 | 14.4 |
| qwen-local | category-only | 41 | N/A | N/A | N/A | 73.2% | 76.7% | 2515.4 | 3532.6 | 18.5 |

평가하지 않은 항목은 0이 아니라 N/A로 표시합니다.
