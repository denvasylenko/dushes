---
title: CLI
description: formguide init, check and serve.
---

The package installs a `formguide` command.

## `formguide init [dir]`

Writes a starter configuration into `dir` (default `.`): `formguide.yaml`, a domain pack and a skill. `--force` overwrites existing files.

## `formguide check`

Loads a configuration and reports it, without calling any model: the model per role (noting a missing API key), domain packs, skills, knowledge, tools, `interrupt_mode`, tracing and the component map. With `--jsx` it also parses the form and lists its warnings.

| Option | Default | Meaning |
| --- | --- | --- |
| `--config` | `formguide.yaml` | the file to load |
| `--jsx` | | also check a form: its JSX file |
| `--form-config` | | with `--jsx`: a sample config JSON `{props, state}`, to check value formats against the field specs |

## `formguide serve`

Runs the agent endpoints (needs the `server` extra).

| Option | Default | Meaning |
| --- | --- | --- |
| `--config` | `$FORMGUIDE_CONFIG`, else `./formguide.yaml` | the file to load |
| `--host` | `127.0.0.1` | |
| `--port` | `8000` | |
| `--prefix` | `/agent` | where the router is mounted |
| `--cors` | | an allowed origin; repeat it; `*` for development |
| `--static` | | serve a built frontend from this folder |

```bash
ANTHROPIC_API_KEY=... formguide serve --config my-agent/formguide.yaml --cors "*"
```
