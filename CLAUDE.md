# formguide — working rules

## Language
Everything in the repository is in English: code, comments, prompts, tool descriptions, demo forms and samples, tests, specs, docs, commit messages. No Cyrillic text anywhere; where code must recognise non-English words (e.g. yes/no in other languages), write them as `\u` escapes with a comment. Check before finishing: `python3 scripts/check_english.py` must print "OK".

## Keep the documentation in sync (always)
Documentation is maintained continuously, in the same change as the code — never "later".

- **Specs** — `openspec/specs/<capability>/spec.md` are the behaviour contracts. For any change in observable behaviour:
  - larger features or anything that needs design: start an OpenSpec change (`/opsx:propose`), implement with `/opsx:apply`, archive with `/opsx:archive` (which syncs the delta into the main specs);
  - small fixes: edit the affected main spec directly in the same change.
  - New capability → new folder under `openspec/specs/`.
- **Architecture** — update `docs/architecture.md` when components, data flow, the turn lifecycle, or configuration change.
- **Architecture pages** — `docs/architecture-pages.html` is the single source of the visual docs. It is published two ways: the GitHub Pages site (built by `scripts/build_docs_site.py`, which also renders `openspec/specs/` into a "Specifications" page; deployed by `.github/workflows/docs.yml` on push to `main`) and the claude.ai artifact https://claude.ai/artifact/6w26keGKcZNXqiGzk5puKN (republish with the Artifact tool, `url` = that link). When `docs/architecture.md` changes in a way the pages show, update the HTML, run `python3 scripts/build_docs_site.py` to check it builds, and republish the artifact.
- **README.md** — update usage, configuration or run instructions when they change.
- Before finishing any task that touched behaviour, run:
  ```bash
  openspec validate --all --strict
  python3 scripts/check_english.py
  cd backend && uv run pytest -q
  ```

## Layout
- `backend/formguide/` — the library (form core, agent graph, domain packs, knowledge, attachments, models, skills, config, optional FastAPI router).
- `backend/demo/` — example integration: mock form backend, FastAPI app, `formguide.yaml`, skills, samples.
- `backend/tests/` — offline tests (scripted model). `backend/scripts/chat_harness.py` — live scenarios against the demo server.
- `frontend/` — optional demo UI.

## Running
- Demo server: `cd backend && ANTHROPIC_API_KEY=... uv run uvicorn demo.app:app --port 8000 --reload --reload-dir formguide --reload-dir demo` (`--reload` watches `.py` only).
- Frontend build: `cd frontend && npm run build` (served by the demo server).

## Git / GitHub
The project will be pushed to a GitHub repository the user will name later. Do not create remotes, commit or push until the user asks and gives the repository.
