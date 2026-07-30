# AI Mix 사이드카 — 제목·요약, 카테고리 분류, 임베딩, 3차원 좌표 축소(UMAP).
# umap-learn(numpy/scikit-learn 계열) 때문에 이미지가 수백 MB지만 크롤러보다는 작다.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements-core.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY woojuin_ai ./woojuin_ai

EXPOSE 8002

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]
