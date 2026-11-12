# Proposal

## Why

formguide's documentation lives in five Markdown files, one long HTML page with diagrams (`docs/architecture-pages.html`, also kept as a claude.ai artifact) and 25 specs glued onto it by a small Python script. There is no search, no navigation across guides, no API reference, and nothing shows what the product feels like without running a server and an API key. A developer deciding whether to try formguide needs to see the chat fill a form in ten seconds and find the right integration path in two clicks.

## What Changes

- **A documentation site built with Astro Starlight** in `site/`: search, light and dark themes, a sidebar, MDX pages, code highlighting, deployed to GitHub Pages by `.github/workflows/docs.yml`.
- **A landing page with a live, scripted demo**: the real `<agui-chat>` widget and a real form, driven by an in-browser agent that replays recorded AG-UI event streams. No backend, no key; works on static hosting.
- **Guides** (quick start, connecting a frontend, CopilotKit, react-hook-form, plain HTML, configuration, domain packs, knowledge, attachments, observability), **concepts** (the architecture pages and their diagrams, ported), a **reference** (HTTP and AG-UI wire format, YAML keys, Python API, `<agui-chat>` attributes, properties and events) and **specifications** rendered from `openspec/specs/` at build time.
- **One source of truth**: the site's pages replace `docs/architecture-pages.html` and its claude.ai artifact; `docs/*.md` content moves into the site and `docs/` is removed, with `scripts/build_docs_site.py`. CLAUDE.md and README point to the site.

## Capabilities

### New Capabilities
- `docs-site`: how the documentation is built, what it contains, and how it stays in sync.

## Impact

- New `site/` (Astro Starlight project); `.github/workflows/docs.yml`; `CLAUDE.md`, `README.md`, the ui-craft skill's surface map.
- Removed: `docs/` (the architecture page, the Markdown docs, the old build output) and `scripts/build_docs_site.py`.
- No library behaviour changes.
