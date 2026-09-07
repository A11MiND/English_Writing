FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY apps/api /app/apps/api
COPY infra/migrations /app/infra/migrations
COPY alembic.ini /app/alembic.ini

RUN pip install --no-cache-dir -e "/app/apps/api[dev]"

WORKDIR /app

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
