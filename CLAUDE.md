# formguide — working rules

## Language
Everything in the repository is in English: code, comments, prompts, tool descriptions, demo forms and samples, tests, specs, docs, commit messages. No Cyrillic text anywhere; where code must recognise non-English words (e.g. yes/no in other languages), write them as `\u` escapes with a comment. Check before finishing: `python3 scripts/check_english.py` must print "OK".

## Keep the documentation in sync (always)
Documentation is maintained continuously, in the same change as the code — never "later".

- **Specs** — `openspec/specs/<capability>/spec.md` are the behaviour contracts. For any change in observable behaviour:
  - larger features or anything that needs design: start an OpenSpec change (`/opsx:propose`), implement with `/opsx:apply`, archive with `/opsx:archive` (which syncs the delta into the main specs);
  - small fixes: edit the affected main spec directly in the same change.
  - New capability → new folder under `openspec/specs/`.
- **Docs site** — `site/` (Astro Starlight) is the single source of all documentation: guides, concepts with diagrams, the reference and a live scripted demo; deployed to GitHub Pages by `.github/workflows/docs.yml` on push to `main`. Pages are Markdown/MDX in `site/src/content/docs/`; the architecture diagrams are inline SVG in `site/src/fragments/*.html` (one per concept page); `openspec/specs/` is rendered into the Specifications section on every build (`site/scripts/specs.mjs`, output not committed).
  - sections: `getting-started/`, `backend/` (server, configuration, models, packs, documents, skills, persistence, prefill, deploy, observability), `frontend/` (clients, widget, cards, themes, tools), `form/` (the form contract), `concepts/` (diagrams), `reference/`. Every page: a one-line `description` (shown under the title), a copyable example, tabs for variants, a diagram (Mermaid fence, or a hand-drawn SVG reused with `<ArchFigure page=… />`) where flow matters, "Next" cards;
  - components, data flow, the turn lifecycle or configuration change → update `concepts/architecture.md` and the concept page (and its diagram fragment) that shows it;
  - a new option, key, endpoint, event or CLI flag → the matching page under `reference/` and the guide that uses it;
  - integration or usage changes → the guide under `backend/`, `frontend/`, `form/` or `getting-started/`;
  - the landing demo (`site/src/demo/`) replays the real widget's events: when card payloads or event shapes change, update the script there too; the card gallery (`site/src/demo/gallery.ts`, page `frontend/card-gallery`) has one specimen per card and variant: a new card or variant gets a specimen there;
  - backend pages show server code only (YAML and Python tabs, HTTP calls), frontend pages browser code only; each backend and widget page ends with "Every option";
  - the site also publishes `llms.txt`, `llms-full.txt` and `<page>.md` (built from the pages, nothing to edit); the docs assistant behind Ask AI (`backend/docs_ai/`, deployed from `deploy/docs-ai/`) reads `llms-full.txt`, so it follows the docs without changes.
  - Check it builds: `cd site && npm run build`.
- **README.md** — update usage, configuration or run instructions when they change.
- Before finishing any task that touched behaviour, run:
  ```bash
  openspec validate --all --strict
  python3 scripts/check_english.py
  cd backend && uv run pytest -q
  cd site && npm run build        # when docs changed
  ```

## UI work
Before any interface change (the `<agui-chat>` widget, its card renderers and texts, the demo form, the examples, the docs pages), load the `ui-craft` skill (`.claude/skills/ui-craft/`): Apple is the anchor (every component looks and behaves like its iOS / macOS counterpart, `references/apple-components.md`), a five-line mini-brief, the eleven laws (one main action, complex in one tap, Undo instead of confirmations, instant, every state designed, like Apple), the type / spacing / radius scales, text rules and the check in the browser (390 px and desktop, light and dark). Known UI debt is in its `references/audit.md`; update it when you fix or find something.
Docs UI uses only the design system in `site/src/components/ui/` (Button, Copy button, Chips, Segmented, Disclosure, Tile, Callout, Link card, Menu, Range, Swatches, Code panel, Badge, Summary, Entry tiles, Masonry, Metrics, Compare; tokens `--fg-*` in `site/src/styles/theme.css`): a new pattern is added there first and shown on the Reference → Design system page (`reference/design-system.mdx`), then used. Rules and the Apple counterpart of each primitive: `.claude/skills/ui-craft/references/docs-components.md`.

## Layout
- `backend/formguide/` — the library (form core, agent graph, domain packs, knowledge, attachments, models, skills, config, optional FastAPI router).
- `backend/demo/` — example integration: mock form backend, FastAPI app, `formguide.yaml`, skills, samples.
- `backend/tests/` — offline tests (scripted model). `backend/scripts/chat_harness.py` — live scenarios against the demo server.
- `frontend/` — optional demo UI.
- `packages/agui-chat/` — the chat widget. `site/` — the documentation site. `backend/docs_ai/` — the docs assistant (Ask AI).

## Running
- Demo server: `cd backend && ANTHROPIC_API_KEY=... uv run uvicorn demo.app:app --port 8000 --reload --reload-dir formguide --reload-dir demo` (`--reload` watches `.py` only).
- Frontend build: `cd frontend && npm run build` (served by the demo server).
- Docs site: `cd site && npm install && npm run dev` (http://localhost:4321/dushes/; `DOCS_BASE` / `DOCS_SITE` change the base path and host; `PUBLIC_ASK_AI_URL=http://localhost:8100/ask/run` turns on Ask AI).
- Docs assistant: `cd backend && ANTHROPIC_API_KEY=... uv run uvicorn docs_ai.app:app --port 8100` (reads `site/dist/llms-full.txt` unless `DOCS_AI_CORPUS` is set).
- Public host (site + Ask AI + demo in one app, as on Fly): build `site` with `DOCS_BASE=/ PUBLIC_ASK_AI_URL=/ai/ask/run PUBLIC_DEMO_URL=/demo/` and `frontend` with `vite build --base /demo/`, then `cd backend && ANTHROPIC_API_KEY=... uv run uvicorn docs_ai.host:app --port 8080`; deploy: `deploy/docs-ai/` (app `dushes-ai`, https://dushes-ai.fly.dev).

## Git / GitHub
The project will be pushed to a GitHub repository the user will name later. Do not create remotes, commit or push until the user asks and gives the repository.
