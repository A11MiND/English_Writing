FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY apps/auth /app/apps/auth

RUN pip install --no-cache-dir -e "/app/apps/auth"

WORKDIR /app

EXPOSE 9000

CMD ["sh", "-c", "uvicorn auth_service.main:app --app-dir /app/apps/auth --host 0.0.0.0 --port ${PORT:-9000}"]
