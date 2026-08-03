# 모델 결과 비교 보고서

## 입력 결과

- C:\Users\SSAFY\ssafy\ai\ai-text\results\20260729-134955-qwen-local\summary-only
- C:\Users\SSAFY\ssafy\ai\ai-text\results\20260729-134955-qwen-local\category-only

| 모델 | 테스트 모드 | 호출 수 | 응답 성공률 | JSON 성공률 | 스키마 성공률 | 카테고리 정확도 | Macro F1 | 평균 응답 시간(ms) | P95(ms) | 평균 TPS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen-local | summary-only | 22 | 100.0% | 100.0% | 100.0% | N/A | N/A | 3637.1 | 4678.5 | 16.6 |
| qwen-local | category-only | 22 | N/A | N/A | N/A | 86.4% | 91.3% | 3593.7 | 5030.5 | 14.8 |

평가하지 않은 항목은 0이 아니라 N/A로 표시합니다.
