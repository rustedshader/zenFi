FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

# Install system dependencies with GPG verification disabled
RUN apt-get update --allow-unauthenticated && \
    apt-get install -y --no-install-recommends --allow-unauthenticated \
    build-essential libpq-dev gcc netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Copy the rest of the application
COPY . .

RUN uv sync --frozen

# Expose the port the app runs on
EXPOSE 8000

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONBUFFERED=1

CMD ["sh", "-c", "uv run fastapi run --host 0.0.0.0 --port 8000"]