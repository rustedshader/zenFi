FROM python:3.12-slim-bookworm

# Copy uv from the astral-sh/uv image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONBUFFERED=1

# Install system dependencies, including curl and unzip for Deno
RUN apt-get update --allow-unauthenticated && \
    apt-get install -y --no-install-recommends --allow-unauthenticated \
    build-essential libpq-dev gcc netcat-traditional curl unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Deno
RUN curl -fsSL https://deno.land/x/install/install.sh | sh
ENV PATH="/root/.deno/bin:${PATH}"

# Copy the rest of the application
COPY . .

# Install Python dependencies
RUN uv sync --frozen

# Expose the port the app runs on
EXPOSE 8000

CMD ["sh", "-c", "uv run fastapi run app/api/main.py --host 0.0.0.0 --port 8000"]