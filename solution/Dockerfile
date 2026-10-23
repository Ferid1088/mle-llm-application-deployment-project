FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY solution ./solution
COPY data ./data
RUN useradd --create-home appuser \
    && mkdir -p solution/generated reports/generated \
    && chown appuser:appuser solution/generated reports/generated
USER appuser

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "solution.deployment_project.app:app", "--host", "0.0.0.0", "--port", "8000"]
