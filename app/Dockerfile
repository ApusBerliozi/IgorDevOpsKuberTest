# Один образ на api и worker — отличается только командой запуска.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY orders ./orders

RUN useradd --uid 10001 --no-create-home app
USER 10001

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

EXPOSE 8000
# api по умолчанию; worker запускается с command: ["python", "-m", "orders.worker"]
CMD ["uvicorn", "orders.api:app", "--host", "0.0.0.0", "--port", "8000"]
