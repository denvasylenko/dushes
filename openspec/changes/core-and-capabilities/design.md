# Design

## Shape

```python
core = Core(config)                                  # knowledge, models, memory, transcripts, attachments, transcription
dushes = Dushes(core, SiteMap.load("site.yaml"),     # the Site agent; Show is on with a site map
                ui=UIAgent(core),                    # Fill: optional; None for a knowledge-only site
                actions=[HostAction(...)],           # Do
                data=[SiteTool(...)])                # Analyze (with chart and table cards)
create_dushes_router(dushes)
```

```yaml
capabilities:                  # one file; a missing key is off
  know: {namespaces: [site, loan_application], researcher: {toolsets: [documents]}}
  show: {site_map: site.yaml, stay_on_forms: true}
  fill: {}                     # the UI agent, with the form adapters and declared forms below
  do: {actions: my_app.actions:ACTIONS}
  analyze: {tools: my_app.data:TOOLS, cards: [chart, table]}
```

`Core` is extracted from `FormGuide`: the attributes Dushes uses today (`knowledge`, `models`, `transcripts`, `attachments`, `transcriber`, `config`) move to it, and `UIAgent` keeps the agent graph, layouts, packs and skills. `FormGuide(config)` becomes `UIAgent(Core(config))` behind the alias, so every current call and test keeps passing during the move. The modules: `formguide/core.py`, `formguide/ui_agent/` (from `agent/` and `guide.py`), `formguide/site/` stays, `formguide/research/` (from `knowledge/research.py`).

Do: a `HostAction(name, description, parameters, run, undo=None)`. With `undo`, the action runs at once and its result line carries Undo (the ui-craft law); without it, it goes through a confirm card. Analyze: data tools are SiteTools whose results may carry a chart or table spec, drawn with the existing chart block.

## Declared forms

```yaml
forms:
  - id: travel_claim
    steps:
      - {group: trip, fields: [destination, start, end]}
      - {group: costs, fields: [kind, amount, receipt]}
    fields:
      kind: {type: choice, options: [hotel, flight, meals], required: true}
      receipt: {type: file, when: "amount > 50"}
      destination: {type: choice, options_from: resolver}     # options(field, values, query)
```

The server holds the form's values for the thread and computes visibility, required and options from the declaration; the UI agent works on it exactly as on a page form (the same tools, the same context block), so no second agent. A parent change runs the recompute: values still valid stay silently; invalid ones are cleared and the result line says which, with Restore (Undo). Validity is always the form's or the server's answer, never the model's. More than about eight fields in view opens a sheet (the widget's, under UI/UX) with the fields, the chat beside it.

## The Researcher

`Researcher(core, toolsets=["documents"])`, called through the same `ask_documents`/`research` tool. The `data` toolset is opt-in: the host provides read tools (their results run with the user's rights) and a sandbox (`sandbox: my_app.sandbox:run`); the Researcher writes SQL or pandas against what those tools return, never against a connection. Without a sandbox the toolset cannot be switched on.

## The submit guard

A tool marked `submit: true` (in `confirm_tools` today) is not bound to the model until `review_form(mode=submit)` reports no blockers and the server accepted the values. When it is bound, calling it shows the summary card; the tool runs only on that card's resume with the card's id. A user message, whatever it says, resolves nothing.

## Not in this change

The data toolset's sandbox itself (a host's), multi-form flows across pages, a visual editor for declared forms.
