FROM python:3.12-slim-bookworm

WORKDIR /workspace

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV PATH="/workspace/.venv/bin:$PATH"

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# Copy source code
COPY backend /workspace/backend
COPY dashboard /workspace/dashboard
COPY .env /workspace/.env

# Expose ports
EXPOSE 8000 8501

# Start script
COPY start.sh /workspace/start.sh
RUN chmod +x /workspace/start.sh

CMD ["python /workspace/run.py"]