FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
WORKDIR /app
RUN pip install --no-cache-dir uv==0.11.6
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
COPY tests ./tests
COPY scripts ./scripts
RUN uv sync --locked \
    && useradd --uid 10001 --create-home app \
    && mkdir -p /app/artifacts \
    && chown -R app:app /app
USER app
ENV PATH="/app/.venv/bin:${PATH}"
EXPOSE 8000
CMD ["uvicorn", "task_api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
