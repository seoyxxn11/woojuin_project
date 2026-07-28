# 이미지 AI 실행 환경 및 인수인계

## 1. 담당 범위

이미지를 입력받아 검색과 카테고리 분류에 필요한 정보를 추출한다.

- 모델: `qwen3-vl:8b-instruct`
- 생성 결과: `title`, `description`, `tags`, `ocr_text`, `objects`, `confidence`
- 원본 메타데이터: EXIF의 GPS 좌표와 촬영 시각
- 제외 범위: 카테고리 최종 선택, S3 저장, DB 저장, Item 상태 변경

이미지 AI는 백엔드 저장 요청과 동기 실행하지 않는다. 백엔드는 먼저
`PROCESSING` 상태로 저장을 완료하고 Redis Streams의 비동기 작업에서 이미지 AI를
호출해야 한다.

## 2. 확정 파일

| 파일 | 용도 |
| --- | --- |
| `config.qwen3vl8b.fast.yaml` | 모델, 타임아웃, 토큰, 이미지 크기 설정 |
| `prompts/analyze_image_fast.txt` | 서비스용 최종 균형형 이미지 분석 프롬프트 |
| `analyze_service_image.py` | 단건 이미지 분석 진입점 |
| `image_service/` | 전처리, 결과 검증, 오류 처리, 백엔드 요청 변환 |
| `providers/ollama_vision.py` | Ollama API 호출 |
| `run_benchmark.py` | 데이터셋 일괄 평가 |
| `tests/test_image_service.py` | 모델 호출 없는 단위 테스트 |
| `docs/image-ai-contract.md` | 백엔드 전달 JSON과 오류 코드 |

`results/`와 자동 생성 보고서는 개발 검증 산출물이며 운영 입력으로 사용하지 않는다.

## 3. 검증된 개발 환경

| 항목 | 검증 값 |
| --- | --- |
| OS | Windows |
| Python | 3.12.12 |
| Ollama | 0.32.1 |
| GPU | NVIDIA GeForce RTX 4070 Laptop GPU |
| VRAM | 8GB |
| 모델 | `qwen3-vl:8b-instruct` |
| 양자화 설정 | `Q4_K_M` |

Python 3.11 이상을 기준으로 한다. 8GB 미만 VRAM, CPU 실행 또는 다른 운영체제에서는
처리 속도와 메모리 사용량을 별도로 확인한다.

## 4. 신규 환경 설치

PowerShell 기준:

```powershell
cd C:\S15P11C105\ai\ai-image
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
ollama pull qwen3-vl:8b-instruct
```

Ollama가 PATH에 없을 때:

```powershell
$env:Path += ";C:\Users\$env:USERNAME\AppData\Local\Programs\Ollama"
ollama list
```

Ollama 앱이 실행 중이 아니면 별도 터미널에서 서버를 유지한다.

```powershell
ollama serve
```

정상 여부:

```powershell
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

모델 목록에 `qwen3-vl:8b-instruct`가 표시되어야 한다.

## 5. 실행 방법

### 단건 서비스 확인

```powershell
cd C:\S15P11C105\ai\ai-image
.\.venv\Scripts\python.exe analyze_service_image.py C:\path\to\image.jpg
```

프로세스 종료 코드는 성공 `0`, 실패 `1`이다. 표준 출력의 JSON에서
`success`, `error_code`, `retryable`을 확인한다.

### 전체 벤치마크

```powershell
.\.venv\Scripts\python.exe run_benchmark.py --config config.qwen3vl8b.fast.yaml
```

특정 샘플:

```powershell
.\.venv\Scripts\python.exe run_benchmark.py `
  --config config.qwen3vl8b.fast.yaml `
  --sample-id SAMPLE_ID
```

데이터와 설정만 확인:

```powershell
.\.venv\Scripts\python.exe run_benchmark.py `
  --config config.qwen3vl8b.fast.yaml `
  --dry-run
```

주의: 현재 `config.yaml`은 없으므로 벤치마크에서는 `--config`를 생략하지 않는다.

## 6. 현재 운영 설정

`config.qwen3vl8b.fast.yaml` 기준:

| 설정 | 값 | 의미 |
| --- | ---: | --- |
| `timeout_seconds` | 120 | Ollama 요청 제한 시간 |
| `context_length` | 8192 | 모델 문맥 크기 |
| `max_new_tokens` | 2000 | 최대 출력 토큰 |
| `temperature` | 0.0 | 결과 재현성 우선 |
| `seed` | 42 | 테스트 재현용 |
| `keep_alive` | -1 | 모델을 메모리에 유지 |
| `max_dimension` | 2048 | 전처리 후 이미지 최대 변 |

`keep_alive: -1`은 반복 처리 속도에는 유리하지만 VRAM을 계속 점유한다. 개발 중 다른
GPU 작업과 충돌하면 Ollama에서 모델을 내리거나 서버를 종료한다. 정확도 재검증 없이
이미지 크기, 프롬프트, 출력 토큰을 낮추지 않는다.

## 7. 백엔드 연결

백엔드 전달 스펙은 `docs/image-ai-contract.md`를 기준으로 한다.

1. 백엔드가 원본 이미지를 S3에 저장하고 Item을 `PROCESSING`으로 생성
2. Redis Streams `woojuin:item-processing`에 작업 발행
3. 워커가 이미지 파일을 준비하고 이미지 AI 실행
4. 성공 결과를 `build_ai_analysis_request`로 텍스트 분류 입력으로 변환
5. 텍스트 분류기가 워크스페이스의 후보 카테고리 안에서 분류
6. 전체 성공 시 `DONE`, 일부만 성공하면 `PARTIAL`, 모두 실패하면 `FAILED`

이미지 AI 결과의 `metadata.latitude`, `metadata.longitude`,
`metadata.captured_at`은 EXIF가 없으면 `null`이다. 모델이 위치나 촬영 시각을
추정해서 채우면 안 된다.

촬영 위치는 다음 책임으로 분리한다.

1. 이미지 AI가 원본 EXIF에서 `captured_at`, `latitude`, `longitude` 추출
2. 백엔드 지도 어댑터가 좌표를 장소명으로 역지오코딩
3. 백엔드가 좌표와 장소명을 Item에 저장
4. 프론트가 저장된 값을 지도뷰에 표시

지도 공급자는 아직 확정되지 않았으므로 이미지 AI 코드에 특정 지도 API를 직접 연결하지 않는다.

## 8. 오류 처리

| 상황 | 확인 및 조치 |
| --- | --- |
| `OLLAMA_UNAVAILABLE` | Ollama 앱/서버와 `127.0.0.1:11434` 확인 후 재시도 |
| `MODEL_NOT_INSTALLED` | `ollama pull qwen3-vl:8b-instruct` 실행 |
| `MODEL_TIMEOUT` | GPU 사용량과 Ollama 로그 확인 후 큐에서 재시도 |
| `EMPTY_MODEL_RESPONSE` | 최대 2회 재시도 후 실패 기록 |
| `INVALID_MODEL_RESPONSE` | 프롬프트·출력 제한·원본 결과 확인 |
| 이미지 형식/크기 오류 | 재시도하지 않고 사용자 입력 오류로 처리 |

재시도 가능한 오류도 무한 재시도하지 않는다. 현재 서비스 내부 최대 시도 횟수는
2회다. 큐 재처리 횟수와 최종 `FAILED` 전환 기준은 백엔드에서 별도로 제한해야 한다.

## 9. 검증 명령

```powershell
cd C:\S15P11C105\ai\ai-image
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q analyze_service_image.py image_service providers tests
.\.venv\Scripts\python.exe run_benchmark.py --config config.qwen3vl8b.fast.yaml --dry-run
```

실제 모델 인수 테스트에서는 OCR이 있는 스크린샷 1장과 일반 사진 1장을 각각 단건
실행해 성공 JSON과 처리 시간을 확인한다.

## 10. 이미지 → 카테고리 통합 테스트

`ai-mix`는 사용하지 않는다. 이미지 결과를 `ai-text`의 Qwen3 8B 분류기로 직접
전달한다. 실행 방법과 정답 파일 형식은 `../../ai-text/readme.md`의
`이미지 추출 결과 → 카테고리 분류` 절을 따른다.

정답 카테고리는 별도 answer key에 보관하며 이미지 AI와 텍스트 모델 프롬프트에
포함하지 않는다. 이를 통해 정답 유출 없이 파이프라인 정확도를 평가한다.

## 11. 알려진 미완료 사항

- 실제 백엔드 Redis 워커에서 이미지 AI 프로세스를 호출하는 코드는 별도 연동 필요
- 운영 배포 환경의 GPU, Ollama 실행 방식, 모델 볼륨 영속화 방식 확정 필요
- 모니터링 지표와 로그 수집 위치 확정 필요
- 운영 백엔드에서 이미지 결과를 텍스트 분류기로 전달하는 실제 워커 연동 필요

## 12. 인수 체크리스트

- [ ] 운영 장비에서 Ollama와 모델 자동 시작 확인
- [ ] 모델 파일 저장 공간과 재시작 후 영속성 확인
- [ ] 단건 이미지 성공·실패 JSON을 백엔드 DTO와 대조
- [ ] Redis 작업이 저장 API 응답을 막지 않는지 확인
- [ ] 재시도 후 `DONE/PARTIAL/FAILED` 상태 전환 확인
- [ ] 이미지 AI 결과가 텍스트 분류 요청으로 정상 변환되는지 확인
- [ ] EXIF가 있는 이미지와 없는 이미지 모두 확인
- [ ] 로그에 원본 이미지, 인증정보, 사용자 개인정보가 남지 않는지 확인
- [ ] 처리 시간, 성공률, 오류 코드별 발생 건수 모니터링 확인
- [ ] 배포 전 스모크 테스트 결과 기록
