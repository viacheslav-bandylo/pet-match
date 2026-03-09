FROM python:3.13-slim AS builder

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .

FROM python:3.13-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY app/ app/
COPY rules.yaml .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
