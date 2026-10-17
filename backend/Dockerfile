FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    AUTO_CREATE_TABLES=true \
    DEMO_MODE=false \
    ENVIRONMENT=production

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir psycopg2-binary==2.9.10 google-genai==1.5.0 firebase-admin==6.6.0

COPY app ./app

# Cloud Run injects PORT; bind to 0.0.0.0
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
