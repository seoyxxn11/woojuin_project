# 우주인 이미지 AI 인수인계서

## 1. 최종 구성

| 역할 | 구성 |
| --- | --- |
| 이미지 정보 추출 | `qwen3-vl:8b-instruct` |
| 이미지 프롬프트 | `prompts/analyze_image_fast.txt` 축약 균형형 |
| 카테고리 분류 | 별도 `qwen3:8b` 텍스트 모델 |
| 이미지 입력 | JPEG, MPO, PNG, WEBP, HEIC/HEIF, 최대 20MB |
| 전처리 | EXIF 회전, RGB 변환, 최대 2048px, JPEG 품질 90 |
| 실행 방식 | Ollama + FastAPI HTTP 서버 |

이미지 모델의 카테고리 선택 제외. 이미지에서 다음 정보만 추출.

```text
title, description, tags, ocr_text, objects, confidence
```

촬영 시각과 GPS는 모델 판단 없이 원본 EXIF에서만 추출.

```text
captured_at, latitude, longitude
```

---

## 2. 개발 내용

1. Qwen3-VL 8B 이미지 정보 추출 모델 선정
2. 상세형·속도형·균형형 비교 후 품질을 유지하며 지시를 압축한 최종 프롬프트 확정
3. 모바일 이미지 형식, 회전, 크기, 색상 형식 통일을 위한 전처리 구현
4. 모델 JSON 검증·복구, 재시도, 오류 코드 구현
5. 검색·분류 활용을 위한 OCR·태그·객체 정규화
6. EXIF 촬영 시각과 GPS 좌표 결과 포함
7. 단건 실행, HTTP 서버, 50장 회귀 테스트, 카테고리 연계 테스트 구성

---

## 3. 프롬프트 설계

최종 프롬프트:

```text
prompts/analyze_image_fast.txt
```

### 설계 원칙

| 원칙 | 적용 내용 |
| --- | --- |
| 역할 제한 | 이미지 저장·검색용 정보 추출기로 역할을 고정 |
| 분류 분리 | 카테고리 이름을 출력하지 않도록 명시 |
| 관찰 중심 | 화면에서 직접 확인되는 정보만 사용 |
| 추측 방지 | 사용자 의도, 신원, 장소, 브랜드를 임의 생성하지 않음 |
| UI 노이즈 제거 | 상태바, 배터리, 댓글 버튼 등 공통 UI 제외 |
| 분류 근거 보존 | 객체·행동·OCR 등 서로 다른 근거를 2개 이상 보존 |
| 검색성 강화 | 구체적 대상, 행동, 장소 유형, 자료 유형, 동의어를 태그에 포함 |
| 출력 고정 | 키가 정해진 JSON 객체 하나만 출력 |

### 판단 흐름

반복 지시를 줄이면서 유지한 모델 판단 흐름:

```text
이미지 유형 판단
→ 중심 대상·행동·장소·객체 관계 확인
→ 화면 UI와 실제 본문 구분
→ 핵심 OCR 추출
→ 객체와 OCR을 함께 해석
→ 검색·분류 근거 보존
→ 고정 JSON 형식으로 출력
```

### 필드 작성 기준

- `title`: 핵심 대상과 상황 또는 자료 유형을 한 문장으로 작성
- `description`: 주제와 자료 유형, 이를 뒷받침하는 시각·OCR 근거를 1~2문장으로 작성
- `tags`: 검색과 분류에 필요한 핵심어 7~10개를 중요도순으로 작성
- `ocr_text`: 상품명, 가격, 날짜, 장소명 등 의미 있는 원문만 유지
- `objects`: 검색·분류에 의미 있는 요소를 중복 없이 최대 10개 작성
- `confidence`: 전체 추출 결과의 확신도를 `0.0~1.0`으로 작성

정답 카테고리, 테스트 파일명, 특정 이미지 전용 예외 규칙 제외.

---

## 4. 사진 처리 흐름

```text
원본 이미지
→ 입력 검증
→ EXIF 추출
→ 회전·RGB·크기·형식 전처리
→ Qwen3-VL 추론
→ JSON 추출·검증
→ OCR·태그·객체 정규화
→ 이미지 분석 JSON 생성
→ classificationText 생성
→ qwen3:8b 카테고리 분류
```

### 4.1 입력과 임시 파일

`serve_image_ai.py`의 HTTP 요청 수신 API:

```http
POST /v1/images/analyze
Content-Type: multipart/form-data
file=<이미지>
```

수신 이미지는 운영 데이터 폴더에 저장하지 않고 임시 파일로 처리.

```text
운영체제 임시 폴더/upload.{원본 확장자}
```

분석 완료 후 임시 폴더와 파일 자동 삭제. 원본 영구 저장은 백엔드 S3 담당 범위.

### 4.2 전처리

`image_service/processing.py`의 `prepare_image()`에서 전처리 수행.

```text
20MB 이하인지 검사
→ 이미지 형식 검사
→ 원본 EXIF 추출
→ EXIF 방향으로 회전
→ RGB 변환
→ 긴 변 최대 2048px 축소
→ JPEG 품질 90으로 변환
```

모델 입력 이미지는 임시 `prepared.jpg`로 생성 후 추론 완료 시 삭제. S3 원본은 변경 없음.

### 4.3 모델 추론

`providers/ollama_vision.py`에서 전처리 이미지와 최종 프롬프트를 Ollama에 전달.

```text
prepared.jpg
+ analyze_image_fast.txt
→ qwen3-vl:8b-instruct
```

### 4.4 결과 검증

`image_service/service.py`와 `image_service/processing.py`의 결과 검증 작업:

- JSON 코드 블록 제거
- JSON 객체 추출
- 필수 필드와 자료형 검사
- 태그·객체 중복 제거
- OCR 문자열 정규화
- `confidence` 범위 정리
- 재시도 가능한 오류 최대 2회 시도

### 4.5 카테고리 분류 입력

`image_service/integration.py`에서 이미지 결과를 다음 텍스트로 변환.

```text
이미지 설명: ...
OCR 텍스트: ...
태그: ...
주요 객체: ...
```

변환 텍스트, `title`, 워크스페이스 후보 카테고리 목록을 `qwen3:8b`에 전달.

이미지 모델과 텍스트 분류 모델의 분리 목적:

- 이미지 추출 결과의 검색·요약 재사용
- 카테고리 목록 변경 시 이미지 재분석 방지
- 사용자 수정 카테고리 데이터의 분류 단계 반영

---

## 5. 폴더 구조

```text
ai/ai-image/
├─ config.qwen3vl8b.fast.yaml       # 최종 모델·전처리 설정
├─ requirements.txt                 # Python 패키지
├─ serve_image_ai.py                # HTTP 서버
├─ analyze_service_image.py         # 단건 실행
├─ run_benchmark.py                 # 데이터셋 실행
├─ evaluate.py                      # 품질 평가
├─ prompts/
│  └─ analyze_image_fast.txt        # 최종 프롬프트
├─ image_service/
│  ├─ service.py                    # 전체 분석 흐름
│  ├─ processing.py                 # 이미지·EXIF 전처리와 결과 정규화
│  ├─ integration.py                # 분류 입력 생성
│  ├─ http_contract.py              # HTTP 응답 생성
│  ├─ models.py                     # 결과 모델
│  └─ errors.py                     # 오류 코드
├─ providers/
│  └─ ollama_vision.py              # Ollama 호출
├─ datasets/
│  ├─ final_50_test.jsonl           # 최종 50장 목록
│  ├─ ground_truth.example.jsonl    # 데이터셋 형식 예시
│  └─ images/                       # 테스트 이미지, Git 제외
├─ results/                         # 원본 실행 결과, Git 제외
├─ reports/
│  └─ final-50-mvp-handoff-report.md
├─ tests/
└─ docs/
   ├─ handover.md
   └─ image-ai-contract.md
```

운영에 필요한 핵심 파일:

```text
config.qwen3vl8b.fast.yaml
requirements.txt
serve_image_ai.py
prompts/
image_service/
providers/
```

`datasets/`, `results/`, `reports/`, `tests/`는 검증·포트폴리오 용도.

---

## 6. 설치

검증 환경:

| 항목 | 환경 |
| --- | --- |
| OS | Windows 11 |
| Python | 3.12.12 |
| Ollama | 0.32.1 |
| GPU | RTX 4070 Laptop GPU |
| VRAM | 8GB |

### 모델 설치

```powershell
ollama pull qwen3-vl:8b-instruct
```

카테고리 분류까지 실행할 경우:

```powershell
ollama pull qwen3:8b
```

설치 확인:

```powershell
ollama list
```

`ollama` 명령을 찾지 못하면:

```powershell
$env:Path += ";C:\Users\$env:USERNAME\AppData\Local\Programs\Ollama"
ollama list
```

### Python 환경

```powershell
cd C:\S15P11C105\ai\ai-image
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

가상환경 활성화가 제한되면 `.venv`의 Python 직접 사용.

---

## 7. 실행

### Ollama 확인

정확도 변경 없이 메모리 사용과 추론 효율 개선을 위한 Ollama 실행 환경:

```powershell
$env:OLLAMA_FLASH_ATTENTION="1"
ollama serve
```

이미 실행 중인 Ollama 프로세스에는 환경변수 미적용. 기존 프로세스 종료 후 위 명령으로 재실행.

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

연결되지 않을 때만 별도 터미널에서 실행.

```powershell
ollama serve
```

### 이미지 AI 서버

```powershell
cd C:\S15P11C105\ai\ai-image
.\.venv\Scripts\python.exe -m uvicorn serve_image_ai:app --host 0.0.0.0 --port 8001
```

상태 확인:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
```

첫 사용자 요청 전 모델 워밍업:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/warmup
```

정상 응답의 `status: READY` 확인 후 서비스 연결. `keep_alive: -1` 설정으로 Ollama 프로세스 종료 전까지 모델 상주.

운영 컨텍스트 `6144`. 최종 50장 최대 실제 사용량 약 5,222토큰을 수용하면서 8GB VRAM의 CPU 분할 실행 감소 목적. 고밀도 OCR 회귀 테스트를 거쳐 최종 확정.

### 단건 실행

```powershell
.\.venv\Scripts\python.exe analyze_service_image.py "C:\path\to\image.jpg"
```

HTTP 실행:

```powershell
curl.exe -X POST http://127.0.0.1:8001/v1/images/analyze `
  -F "file=@C:\path\to\image.jpg"
```

### 최종 50장

파일 확인만 수행:

```powershell
.\.venv\Scripts\python.exe run_benchmark.py `
  --config config.qwen3vl8b.fast.yaml `
  --dry-run
```

실제 실행:

```powershell
.\.venv\Scripts\python.exe run_benchmark.py `
  --config config.qwen3vl8b.fast.yaml
```

특정 한 장:

```powershell
.\.venv\Scripts\python.exe run_benchmark.py `
  --config config.qwen3vl8b.fast.yaml `
  --sample-id final50-001
```

---

## 8. 결과 확인

### 단건 결과

단건 명령과 HTTP 요청 결과는 터미널에 출력.

```json
{
  "success": true,
  "result": {
    "title": "러닝 기록 화면",
    "description": "Nike Run Club 달리기 기록 화면이다.",
    "tags": ["러닝", "운동 기록", "Nike Run Club"],
    "ocr_text": "3.02 킬로미터 16:36 212 칼로리",
    "objects": ["스마트폰 화면", "지도", "달리기 경로"],
    "confidence": 0.96
  },
  "classificationText": "이미지 설명: ...",
  "metadata": {
    "captured_at": null,
    "latitude": null,
    "longitude": null
  }
}
```

스크린샷이나 메신저 저장 사진은 EXIF가 없어 메타데이터 `null`이 정상.

### 벤치마크 결과

```text
ai/ai-image/results/<실행시각>/
```

원본 JSONL에 이미지별 추출 결과, 전처리 정보, EXIF, 처리 시간, 오류 저장. 재검토·포트폴리오 근거 자료로 유지.

### 카테고리 결과

```text
ai/ai-text/results/<실행시각>-image-to-category/
├─ results.jsonl
├─ details.csv
└─ report.md
```

- `results.jsonl`: 모델 원본 분류 결과
- `details.csv`: 이미지별 정답 비교
- `report.md`: 정확도와 불일치 요약

---

## 9. 품질 결과

### 이미지 추출 50장

| 항목 | 결과 |
| --- | ---: |
| 구조화 추출 성공률 | **100.0% (50/50)** |
| 평균 처리 시간 | **26.78초** |
| 중앙 처리 시간 | **19.72초** |
| P95 처리 시간 | **62.37초** |
| 최소 / 최대 처리 시간 | 10.69초 / 85.75초 |
| 핵심 개념 재현율 | **81.4% (118/145)** |
| OCR 핵심어 재현율 | **85.3% (64/75)** |
| GPS EXIF 추출 | **12/50** |
| 촬영 시각 EXIF 추출 | **19/50** |

최종 실행:

```text
results/20260729-102204-qwen3-vl_8b-instruct.jsonl
```

이전 균형형 50장 대비 평균 처리 시간 32.20초에서 26.78초로 **16.8% 단축**.
출력 토큰은 평균 343.42개에서 287.76개로 16.2% 감소. 핵심 개념 재현율은
2.0%p, OCR 핵심어 재현율은 1.4%p 감소. 전체 성공률과 JSON 유효성 100% 유지.
P95와 최대 시간은 긴 OCR·상품 화면의 출력량 때문에 개선되지 않았으므로 저장 요청과
분리된 비동기 처리 필수.

### 카테고리 분류 50장

| 기준 | 결과 |
| --- | ---: |
| 허용 정답 기준 Top-1 | **50/50 (100%)** |
| 대표 정답 완전 일치 | **47/50 (94%)** |
| 평균 분류 시간 | **1.84초** |

100%는 개발 데이터의 복수 허용 정답 기준. 신규 사용자 데이터의 동일 정확도 보장을 의미하지 않음.
카테고리 수치는 `20260728-105624` 이미지 추출 결과에 대한 분류 결과. 최종 축약
프롬프트의 `20260729-102204` 결과로 카테고리 모델을 다시 실행한 수치는 아님.

상세 보고서:

```text
reports/final-50-mvp-handoff-report.md
```

---

## 10. 검증 명령

이미지 AI 단위 테스트:

```powershell
cd C:\S15P11C105\ai\ai-image
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

문법 검사:

```powershell
.\.venv\Scripts\python.exe -m compileall -q `
  analyze_service_image.py `
  serve_image_ai.py `
  image_service `
  providers `
  tests
```

카테고리 연계 테스트:

```powershell
cd C:\S15P11C105\ai\ai-text
.\.venv\Scripts\python.exe -m pytest tests\test_image_category_pipeline.py -q
```

최종 확인 결과:

```text
이미지 AI 단위 테스트 24개 통과
이미지→카테고리 연계 테스트 6개 통과
최종 50장 dry-run 통과
```

---

## 11. 오류 확인

| 오류 | 조치 |
| --- | --- |
| `OLLAMA_UNAVAILABLE` | Ollama 프로세스와 `127.0.0.1:11434` 확인 |
| `MODEL_NOT_INSTALLED` | `ollama pull qwen3-vl:8b-instruct` |
| `MODEL_TIMEOUT` | GPU·VRAM 사용량과 Ollama 로그 확인 |
| `IMAGE_TOO_LARGE` | 원본을 20MB 이하로 제한 |
| `UNSUPPORTED_IMAGE` | 입력 형식과 `pillow-heif` 설치 확인 |
| `IMAGE_DECODE_FAILED` | 손상 파일 또는 확장자 불일치 확인 |
| `INVALID_MODEL_RESPONSE` | 원본 모델 응답과 프롬프트 확인 |
| 첫 장만 느림 | 모델의 최초 VRAM 적재 시간 확인 |
| 계속 느림 | Ollama가 GPU를 사용하는지 확인 |

---

## 12. 전달 항목

Git으로 전달:

```text
ai/ai-image/config.qwen3vl8b.fast.yaml
ai/ai-image/requirements.txt
ai/ai-image/serve_image_ai.py
ai/ai-image/analyze_service_image.py
ai/ai-image/run_benchmark.py
ai/ai-image/prompts/
ai/ai-image/image_service/
ai/ai-image/providers/
ai/ai-image/tests/
ai/ai-image/docs/
ai/ai-image/reports/final-50-mvp-handoff-report.md
ai/ai-image/datasets/final_50_test.jsonl
ai/ai-image/datasets/ground_truth.example.jsonl
```

별도 전달:

```text
ai/ai-image/datasets/images/
ai/ai-image/results/
```

전달하지 않는 파일:

```text
.venv/
.env
실제 API 키
개인정보가 포함된 로그
```

인수 장비에서 Ollama 모델 직접 설치.

```powershell
ollama pull qwen3-vl:8b-instruct
```

최초 인수 확인 대상: 일반 사진 1장, OCR 스크린샷 1장, EXIF 포함 원본 사진 1장.
