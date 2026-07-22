# AI Image 로컬 모델 벤치마크

이미지 분석·OCR·카테고리·태그 생성 성능을 동일한 데이터와 프롬프트로 비교하는
독립 실행형 실험 코드입니다. 이 폴더 밖의 서비스 코드와는 연결하지 않습니다.

## 기본 모델

- 현재 비교 대상: `google/gemma-3-12b-it`
- 실행 방식: Hugging Face Transformers
- 기본 양자화: 4비트

Gemma 3 4B 기준 테스트를 완료했으며, 현재는 같은 데이터로 12B 모델을 비교하는
단계입니다. 8GB VRAM에 모델 전체가 들어가지 않으면 `device_map: auto`가 일부를
시스템 RAM으로 넘길 수 있어 처리 속도가 크게 느려질 수 있습니다.

## 폴더 구조

```text
ai-image/
├─ config.yaml
├─ requirements.txt
├─ prompts/analyze_image.txt
├─ datasets/
│  ├─ images/
│  └─ ground_truth.example.jsonl
├─ providers/
│  ├─ base.py
│  └─ gemma.py
├─ results/
├─ reports/
├─ run_benchmark.py
├─ evaluate.py
├─ search.py
└─ report.py
```

## 1. 환경 준비

Python 3.11 또는 3.12와 NVIDIA 드라이버가 필요합니다.

```powershell
cd ai/ai-image
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Hugging Face에서 Gemma 사용 조건에 동의한 뒤 로그인합니다.

```powershell
huggingface-cli login
```

토큰을 파일에 저장하고 싶지 않으면 세션 환경변수로 전달할 수 있습니다.

```powershell
$env:HF_TOKEN="본인의 Hugging Face 토큰"
```

토큰이나 모델 파일은 Git에 커밋하지 마세요.

## 2. 테스트 이미지 등록

1. 이미지를 `datasets/images/`에 넣습니다.
2. `ground_truth.example.jsonl`을 복사해 `ground_truth.jsonl`을 만듭니다.
3. 이미지 한 장당 JSON 한 줄을 작성합니다.

```json
{"id":"receipt-001","file":"images/receipt-001.jpg","category":"DOCUMENT","ocr_text":"아메리카노 4500원","required_tags":["영수증","카페"]}
```

`category`는 다음 값 중 하나를 사용합니다.

```text
DOCUMENT, FOOD, PLACE, PRODUCT, PERSON, SCREENSHOT, OTHER
```

정답을 아직 만들지 못한 항목은 빈 값으로 둘 수 있습니다.

## 3. 실행

먼저 설정과 데이터만 검증합니다. 이 명령은 모델을 내려받지 않습니다.

```powershell
python run_benchmark.py --dry-run
```

전체 데이터셋을 실행합니다.

```powershell
python run_benchmark.py
```

특정 이미지 한 장만 실행할 수도 있습니다.

```powershell
python run_benchmark.py --sample-id receipt-001
```

결과는 `results/<실행시각>-gemma-3-4b-it.jsonl`에 저장됩니다. 중간에 실패해도
이미 처리된 결과는 보존됩니다. 실행이 끝나면 기존 결과를 모두 읽어 비교 보고서도
자동으로 갱신합니다.

```text
reports/model-comparison.md  # VS Code에서 읽기 좋은 종합 보고서
reports/model-summary.csv    # 모델·실행별 지표
reports/sample-details.csv   # 이미지별 정답과 예측 결과
reports/search-indexes/      # 실행별 검색 가능한 이미지 정보
```

## 4. 평가

```powershell
python evaluate.py --result results/<결과파일>.jsonl
```

다음 지표가 출력됩니다.

- 성공률과 JSON 파싱 성공률
- 평균 및 P95 처리 시간
- 카테고리 정확도
- 카테고리 검색 Precision, Recall, F1
- OCR 문자 오류율(CER)
- 필수 태그 재현율

이미지 설명 품질과 환각 여부는 자동 점수만으로 판단하기 어려우므로 결과 파일에
사람 평가 점수를 추가해 별도로 비교하는 것을 권장합니다.

기존 결과만으로 보고서를 다시 만들고 싶다면 다음 명령을 실행합니다.

```powershell
python report.py
```

모델을 비교할 때는 각 모델을 동일한 전체 데이터셋으로 실행해야 합니다. 한 장만
실행한 결과와 다섯 장을 실행한 결과의 정확도를 직접 비교하면 안 됩니다.

## 5. 카테고리로 이미지 검색

모델 실행 결과에는 이미지 파일, 제목, 설명, 카테고리, 태그, OCR, 주요 객체가
검색 인덱스로 저장됩니다. 가장 최근 실행 결과에서 문서 이미지를 검색하려면:

```powershell
python search.py --category DOCUMENT
python search.py --category 문서
```

특정 모델 실행 결과를 검색하려면:

```powershell
python search.py --category FOOD --result results/<결과파일>.jsonl
```

이 검색은 운영 서비스의 데이터베이스를 대신하는 로컬 테스트입니다. 실제 서비스에서는
동일 필드를 아이템 레코드와 검색 인덱스에 저장하고 워크스페이스 권한을 검증한 뒤
검색해야 합니다.

## 설정값

`config.yaml`에서 모델과 생성 옵션을 바꿀 수 있습니다.

```yaml
model:
  model_id: google/gemma-3-12b-it
  quantization: 4bit
  device_map: gemma_12b_laptop
  cpu_offload: true
  max_new_tokens: 512
  temperature: 0.0
```

모델을 공정하게 비교하려면 데이터셋과 프롬프트는 유지하고 `model_id` 및 실행
옵션만 변경하세요.

12B 모델은 8GB VRAM에 전부 들어가지 않으므로 `gemma_12b_laptop` 장치 배치를
사용합니다. 비전 인코더·임베딩·출력 헤드는 시스템 RAM에, 언어 모델 레이어는 GPU에
배치합니다. 이 경우 품질 비교는 가능하지만 처리 시간은 GPU에 모델 전체를 올린
환경보다 느립니다. 보고서에서 4B와 12B 속도를 비교할 때 이 실행 조건을 함께 기록해야
합니다.
