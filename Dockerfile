# JARVIS AI - server image
# Browser control chahiye?  docker build --build-arg WITH_BROWSER=1 -t jarvis .
FROM python:3.12-slim

ARG WITH_BROWSER=0
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 BROWSER_HEADLESS=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN if [ "$WITH_BROWSER" = "1" ]; then \
      apt-get update && apt-get install -y --no-install-recommends \
        libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
        libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
        libasound2 fonts-liberation && \
      playwright install chromium && rm -rf /var/lib/apt/lists/*; \
    fi

COPY . .
RUN mkdir -p projects
EXPOSE 8000
CMD ["sh", "-c", "cd backend && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
