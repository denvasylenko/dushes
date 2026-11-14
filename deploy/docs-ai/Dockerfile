# formguide's public host: the docs site, Ask AI and the live demo in one app (backend/docs_ai/host.py).
# Build context: the repository root.
#   fly deploy . --config deploy/docs-ai/fly.toml --dockerfile deploy/docs-ai/Dockerfile --ignorefile deploy/docs-ai/.dockerignore
ARG SITE_URL=https://dushes-ai.fly.dev

# 1. the one-script widget (for the playground), the docs site (with Ask AI, demo and playground) and the demo page
FROM node:24-slim AS web
ARG SITE_URL
WORKDIR /src
COPY packages/agui-chat/package.json packages/agui-chat/package-lock.json packages/agui-chat/
RUN cd packages/agui-chat && npm ci
COPY site/package.json site/package-lock.json site/
RUN cd site && npm ci
COPY frontend/package.json frontend/package-lock.json frontend/
RUN cd frontend && npm ci
COPY packages/agui-chat packages/agui-chat
COPY openspec openspec
COPY site site
COPY frontend frontend
# the one-script build and its on-demand files next to it: language and theme packs (agui-chat.lang-*.js,
# agui-chat.theme-*.js), the markup editor (agui-chat.editor.js), the shortcut tooltip (agui-chat.tip.js), the field highlight (agui-chat.highlight.js), the card blocks (agui-chat.blocks.js) and Chart.js
# for the charts in cards (agui-chat.charts.js)
RUN cd packages/agui-chat && npx vite build --config vite.iife.config.ts && npx vite build --config vite.editor.config.ts && npx vite build --config vite.tip.config.ts && npx vite build --config vite.highlight.config.ts && npx vite build --config vite.blocks.config.ts && npx vite build --config vite.charts.config.ts && node scripts/lang-files.mjs
RUN cd site && DOCS_SITE=$SITE_URL DOCS_BASE=/ PUBLIC_ASK_AI_URL=/ai/ask/run PUBLIC_DEMO_URL=/demo/ \
    PUBLIC_DEMO_AGENT_URL=/agent/run PUBLIC_PLAYGROUND_URL=/examples/widget/ npm run build
RUN cd frontend && npx vite build --base /demo/

# 2. the server
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/
RUN cd backend && uv sync --frozen --no-dev --extra all --no-install-project
COPY backend backend
COPY --from=web /src/site/dist site/dist
COPY --from=web /src/frontend/dist frontend/dist
COPY --from=web /src/packages/agui-chat/dist packages/agui-chat/dist
COPY examples/widget-html examples/widget-html
RUN cd backend && uv sync --frozen --no-dev --extra all
WORKDIR /app/backend
EXPOSE 8080
CMD ["uv", "run", "--no-sync", "uvicorn", "docs_ai.host:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]
