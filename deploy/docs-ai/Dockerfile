# The docs assistant (backend/docs_ai) for the site's Ask AI. Build context: the repository root.
#   fly deploy . --config deploy/docs-ai/fly.toml --dockerfile deploy/docs-ai/Dockerfile   (from the repository root)
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/
RUN cd backend && uv sync --frozen --no-dev --extra server --extra anthropic --no-install-project
COPY backend/formguide backend/formguide
COPY backend/docs_ai backend/docs_ai
RUN cd backend && uv sync --frozen --no-dev --extra server --extra anthropic
WORKDIR /app/backend
EXPOSE 8080
CMD ["uv", "run", "--no-sync", "uvicorn", "docs_ai.app:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]
