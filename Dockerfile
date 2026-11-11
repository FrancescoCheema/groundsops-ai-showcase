FROM python:3.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update \
    && apt-get install --only-upgrade -y --no-install-recommends zlib1g \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts
RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 groundsops
USER groundsops

EXPOSE 8000
CMD ["uvicorn", "groundsops.main:app", "--host", "0.0.0.0", "--port", "8000"]
