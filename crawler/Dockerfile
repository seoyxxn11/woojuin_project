# Scrapling 크롤러 사이드카. 브라우저(camoufox)를 번들하므로 이미지가 크다.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# camoufox/Playwright 계열 브라우저가 필요로 하는 공용 시스템 라이브러리.
# scrapling install이 브라우저 바이너리는 받아오지만, 실행에 필요한 .so는
# 이미지에 미리 깔려 있어야 한다.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgtk-3-0 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 \
        libgbm1 libxkbcommon0 libasound2 libpango-1.0-0 libcairo2 \
        libdbus-glib-1-2 libnss3 libatk1.0-0 libatk-bridge2.0-0 fonts-liberation \
        ca-certificates wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 브라우저 바이너리(camoufox 등) 다운로드. 빌드 타임에 받아둬 런타임 지연을 없앤다.
RUN scrapling install

COPY main.py .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
