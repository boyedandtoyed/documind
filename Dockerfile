FROM python:3.11-slim AS base
WORKDIR /app
RUN pip install --no-cache-dir uv

FROM base AS builder
COPY pyproject.toml .
RUN uv pip install --system --no-cache -r pyproject.toml

FROM builder AS runner
COPY src/ ./src/
COPY .env.example .env
ENV PYTHONPATH=/app/src
EXPOSE 8000
CMD ["uvicorn", "documind.api:app", "--host", "0.0.0.0", "--port", "8000"]
