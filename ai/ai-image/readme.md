# 이미지 AI

Qwen3-VL 8B를 사용해 이미지에서 검색·분류에 필요한 텍스트 정보를 추출하는
MVP 모듈입니다. 이미지 모델은 카테고리를 선택하지 않으며, 추출 결과를 별도의
텍스트 분류 단계에 전달합니다.

## 확정 구성

- 모델: `qwen3-vl:8b-instruct`
- 설정: `config.qwen3vl8b.fast.yaml`
- 프롬프트: `prompts/analyze_image_fast.txt`
- 입력: JPEG, MPO, PNG, WEBP, HEIC/HEIF, 최대 20MB
- 전처리: EXIF 회전 보정, RGB 변환, 최대 2048px 리사이즈
- 출력: 제목, 설명, 태그, OCR, 객체, 신뢰도, EXIF 메타데이터
- 오류 처리: 재시도 가능한 오류는 최대 2회 시도
- 실행 위치: 백엔드 저장 요청과 분리된 비동기 작업

입출력 필드와 오류 코드는 `docs/image-ai-contract.md`를 확인합니다.

## 환경 준비

Python 3.11 이상과 Ollama가 필요합니다. 현재 검증한 개발 환경은 Windows,
Python 3.12.12, Ollama 0.32.1, RTX 4070 Laptop GPU(8GB VRAM)입니다.
다른 GPU나 CPU 환경에서는 처리 시간과 메모리 사용량을 다시 확인해야 합니다.

```powershell
cd C:\S15P11C105\ai\ai-image
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
ollama pull qwen3-vl:8b-instruct
```

Ollama 앱이 자동 실행되지 않는 환경에서는 서버를 실행합니다.

```powershell
ollama serve
```

PowerShell에서 `ollama` 명령을 찾지 못하면 Ollama 설치 경로를 현재 터미널의
PATH에 추가합니다.

```powershell
$env:Path += ";C:\Users\$env:USERNAME\AppData\Local\Programs\Ollama"
ollama list
```

## 단건 실행

```powershell
cd C:\S15P11C105\ai\ai-image
.\.venv\Scripts\python.exe analyze_service_image.py C:\path\to\image.jpg
```

결과 JSON의 `result`에는 제목·설명·태그·OCR·객체·신뢰도가 포함됩니다.
원본에 EXIF가 있으면 `metadata`에 좌표와 촬영 시간이 추가됩니다.

## 카테고리 분류 연결

이미지 추출 결과는 `build_ai_analysis_request`로 최신 백엔드
`AiAnalysisRequest(title, text, candidateCategories)` 형식에 맞춥니다.

```python
from image_service import build_ai_analysis_request

request = build_ai_analysis_request(image_result, candidate_categories)
```

`candidate_categories`는 해당 워크스페이스에 실제 존재하는 카테고리 이름 목록이며,
이미지 모델은 이 값을 판단하거나 변경하지 않습니다.

## 백엔드 연동용 HTTP 서버

Ollama 서버를 먼저 실행한 뒤 이미지 AI 서버를 실행합니다.

```powershell
cd C:\S15P11C105\ai\ai-image
.\.venv\Scripts\python.exe -m uvicorn serve_image_ai:app --host 0.0.0.0 --port 8001
```

백엔드는 `POST /v1/images/analyze`에 이미지 파일을 multipart `file`로 전달합니다.
성공 응답의 `classificationText`를 현재 백엔드
`ImageTextExtractor.extract(byte[])`의 반환값으로 사용하면 됩니다.

```powershell
curl.exe -X POST http://127.0.0.1:8001/v1/images/analyze `
  -F "file=@C:\path\to\image.jpg"
```

상태 확인:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
```

## 검증

모델을 실행하지 않고 전처리·JSON 검증·재시도·연동 변환을 테스트합니다.

```powershell
cd C:\S15P11C105\ai\ai-image
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q analyze_service_image.py image_service providers tests
```

전체 데이터셋 벤치마크는 설정 파일을 명시해 실행합니다.

```powershell
.\.venv\Scripts\python.exe run_benchmark.py --config config.qwen3vl8b.fast.yaml
```

현재 저장소에는 `run_benchmark.py`의 기본 설정명인 `config.yaml`이 없으므로
`--config`를 생략하면 실행되지 않습니다.

최종 33장 품질 결과는 `reports/final-33-evaluation-report.md`에 정리되어 있습니다.
설정값, 운영 흐름, 장애 대응과 인수 체크리스트는
`docs/handover.md`를 확인합니다.
