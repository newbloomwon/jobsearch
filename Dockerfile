FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for layer caching.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install ".[api,resume,scrapers]"

EXPOSE 8000
ENV PORT=8000

# Scrapes can take ~60s; keep idle connections alive behind proxies.
CMD ["sh", "-c", "uvicorn jobsearch_api.main:app --host 0.0.0.0 --port \"${PORT:-8000}\" --timeout-keep-alive 75"]
