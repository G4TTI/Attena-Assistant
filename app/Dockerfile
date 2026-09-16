FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DB_PATH=/app/data/app.db

WORKDIR /srv

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY whatsapp_scheduler ./whatsapp_scheduler

RUN mkdir -p /app/data \
    && groupadd --system app && useradd --system --gid app --home /srv app \
    && chown -R app:app /srv /app/data
USER app

EXPOSE 8000

CMD ["uvicorn", "whatsapp_scheduler.main:app", "--host", "0.0.0.0", "--port", "8000"]
