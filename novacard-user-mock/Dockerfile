FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir fastapi uvicorn python-jose[cryptography] pydantic-settings redis prometheus-client

EXPOSE 8002
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]