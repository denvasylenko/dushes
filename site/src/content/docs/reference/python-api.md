---
title: Python API
description: FormGuide, its methods, the config objects and the app factories.
---

```python
from formguide import FormGuide, GuideConfig, load_config, Models, KnowledgeBase, BM25Index, VectorStoreIndex, \
    SkillRegistry, DomainPackRegistry
```

## Building a guide

| Call | Does |
| --- | --- |
| `load_config(path)` | reads `formguide.yaml` into a `GuideConfig` (unknown keys fail with their name) |
| `GuideConfig(...)` | the same in code: models, domain packs, knowledge, skills, tools, stores, memory, `interrupt_mode` |
| `FormGuide(config)` | the guide: the agent graph and everything it needs |
| `formguide.app.create_app(config, prefix="/agent", cors=[...])` | a whole FastAPI app |
| `formguide.server.create_router(guide, debug=False)` | the router for your own app ([HTTP API](../http-api/)) |

## `FormGuide` methods

| Method | Does |
| --- | --- |
| `register_form(jsx, form_id=None, domain=None, config=None)` | parse and cache a layout once per JSX; optionally register a domain pack shipped with the form. Returns `{jsx_hash, ...}` and warnings |
| `async run(thread_id, *, message=None, state=None, resume=None, run_id=None, client_tools=None, tool_results=None, prefill=None)` | one turn as AG-UI events (dicts with camelCase keys) |
| `async suggest_prefill(state, *, data=None, text=None, attachment_ids=None, thread_id=None)` | validated values for the form from data the app already has |
| `thread(thread_id, form_id=None)` | the display transcript and the pending card |
| `thread_messages(thread_id)` | the transcript as AG-UI messages |
| `async delete_thread(thread_id)` | forget a conversation |
| `add_document(namespace, filename, data)` / `delete_document(namespace, doc_id)` | manage business documents |
| `async compile_knowledge(form_id, jsx, config)` | compile the documents in the form's scope into its domain pack |
| `save_attachment(thread_id, filename, data)` | store a user document for the next run |
| `async history(thread_id)` / `recent_runs(thread_id)` | the model's history and recent run stats, for debugging |

`run` takes, for a new message, `message` + `state = {config, jsx_hash, form_id, ui?, attachments?}`; after a field-change card, `resume = {accepted, config?, ui?, names?, comment?}`; after a question, `resume = {answer: {ids?, text?}}` (`{accepted: False}` skips).

Every key of `GuideConfig` and its YAML form: [Configuration](../configuration/#every-key).
