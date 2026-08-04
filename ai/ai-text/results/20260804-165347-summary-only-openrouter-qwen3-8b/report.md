# AI 텍스트 모델 비교 보고서: summary-only

## 실행 정보

- 데이터셋: tester:url
- 데이터 수: 5
- testId: URL-001, URL-002, URL-003, URL-004, URL-005
- 프롬프트 버전: v1
- 실행 일시: 2026-08-04T16:53:48.347461+09:00 ~ 2026-08-04T16:54:03.833447+09:00
- 스트리밍/외부 검색/도구 사용: 모두 비활성화
- 구조화 출력:
- openrouter-qwen3-8b: 요청=true, 적용=5건, fallback=0건

## 형식 안정성 및 모델 성능

| Model ID | Provider | Model | 호출 수 | 성공률 | JSON 성공률 | Schema 성공률 | Category Accuracy | Macro F1 | 필수 키워드 | 요약 핵심 | 원문 키워드 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| openrouter-qwen3-8b | openrouter | qwen/qwen3-8b | 5 | 100.0% | 100.0% | 100.0% | N/A | N/A | N/A | N/A | N/A |

## 세부 품질 지표

| Model ID | JSON 외 텍스트 | think 노출 | Macro Precision | Macro Recall | 평균 confidence | 정답 confidence | 오답 confidence | 금지 표현 | 태그 개수 | 키워드 개수 | 태그 중복 없음 | 키워드 중복 없음 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| openrouter-qwen3-8b | 0.0% | 0.0% | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

## 운영 지표

| Model ID | 평균(ms) | 중앙값(ms) | P95(ms) | 최소(ms) | 최대(ms) | 입력 토큰 | 출력 토큰 | 예상 비용(USD) | 성공 요청당 비용 |
|---|---|---|---|---|---|---|---|---|---|
| openrouter-qwen3-8b | 9229.162 | 8840.988 | 11201.613 | 6731.447 | 11379.683 | 4231 | 2523 | N/A | N/A |

평가 대상이 아니거나 정답 데이터가 없는 지표는 0이 아니라 N/A로 표시합니다.

## 운영 지표 해석

- Ollama와 OpenAI가 보고하는 토큰 수의 측정 기준은 서로 다를 수 있습니다.
- 가격이 설정되지 않은 모델의 예상 비용과 성공 요청당 평균 비용은 N/A입니다.
- OpenAI 호출에는 temperature, seed, context length를 억지로 적용하지 않았습니다.

## 주요 실패 사례

- 없음

## 주요 혼동 카테고리

- openrouter-qwen3-8b: 없음

## 카테고리별 분류 지표

N/A

## 결론

- 가장 정확한 모델: openrouter-qwen3-8b
- 가장 빠른 모델: openrouter-qwen3-8b
- JSON 형식이 가장 안정적인 모델: openrouter-qwen3-8b
- 비용 기준 운영 후보: N/A (가격 미설정)
- 로컬 모델은 외부 API 비용과 네트워크 의존성이 없고, API 모델은 서버 자원 대신 사용량·지연·비용 관리가 필요합니다.
- 현재 결과는 선택한 데이터 수에 한정되므로 작은 --limit 실행만으로 일반화하지 마세요.
- 비용 대비 성능은 정확도, 지연 시간, 토큰, 실제 가격을 함께 보고 판단해야 합니다.
