# 모델 결과 비교 보고서

## 입력 결과

- C:\Users\SSAFY\ssafy\ai\ai-text\results\20260729-135615-qwen-local\summary-only
- C:\Users\SSAFY\ssafy\ai\ai-text\results\20260729-135615-qwen-local\category-only

| 모델 | 테스트 모드 | 호출 수 | 응답 성공률 | JSON 성공률 | 스키마 성공률 | 카테고리 정확도 | Macro F1 | 평균 응답 시간(ms) | P95(ms) | 평균 TPS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen-local | summary-only | 22 | 100.0% | 100.0% | 100.0% | N/A | N/A | 3688.0 | 4566.8 | 17.2 |
| qwen-local | category-only | 21 | N/A | N/A | N/A | 81.0% | 81.5% | 2898.0 | 3097.8 | 14.5 |

평가하지 않은 항목은 0이 아니라 N/A로 표시합니다.
