# Design

## Configuration

```yaml
models:
  agent: {provider: anthropic, model: claude-haiku-5-5, max_tokens: 16000, effort: low}
  choices:
    haiku: {label: "Haiku"}                       # no roles named: the models above
    luna:
      label: "Luna (experimental)"
      agent: {provider: openai, model: gpt-6-luna, max_tokens: 16000, effort: low}
```

- The first choice is the default. A choice may name `agent`, `research`, `compile`, `extract`, `memory`, `suggestions`; a role it does not name is the choice's `agent` when the choice has one, else the server's own model for that role. So `luna: {agent: …}` puts the helpers and the researcher on Luna too (the CPO's decision b), and a host that wants only the talking agent switched names the other roles.
- `label` is what a client shows. `models.choices` joins `formguide.config.KEYS`.
- A choice whose provider key is missing in the environment is configured but not usable; `FormGuide.model_choices()` reports `[{name, label, default, usable}]`.

## A run's choice

- AG-UI: `forwardedProps.model: "luna"`. Python: `guide.run(thread, ..., model="luna")`, `dushes.run(..., model="luna")`.
- Unknown name: `ValueError` in Python, HTTP 422 with the list of names. A choice that is not usable: 422 "not available on this server".
- With no choices configured, `model` is refused too (422): a server never takes a model from a request unless its owner listed choices.

Inside the run the choice is a context variable; `guide.models`, `guide.suggestions_model` and `guide.translation_model` read it, so the graph, the tools, the researcher and Dushes need no other change. Every choice's models are built once, at start.

## A conversation keeps its model

A thread's history holds one provider's reasoning blocks, tool-call ids and a frozen system prompt; handing it to another provider breaks in ways that differ per provider. So the first run of a thread writes a `model` entry into its transcript (`{choice}`), and later runs:
- name no choice: the thread's choice is used;
- name the same choice: fine;
- name another: HTTP 409 `{code: "model_fixed", choice: <the thread's>}`; the page starts a new thread.

Under Dushes the site thread decides, and its form threads (`<site>-<form>`) follow it.

## The event

When choices are configured every run sends, right after `RUN_STARTED`, `CUSTOM model` `{choice, label, model}` (`model` is the agent's model id). `run_stats` is unchanged: each call line already carries the real model id.

## The demo host

- Choices come from `backend/demo/formguide.hosted.yaml`; the host adds nothing a config cannot say.
- `GET /agent/models` → `{choices: [{name, label, default, usable, left}]}`; `left` is false when that choice's budget for the day is used up.
- Prices: `DEMO_PRICES_FILE` (default `site/src/data/prices.json`, the file the docs' cost columns use), looked up by the model id of each `run_stats` line, its `over` tier included. `DEMO_PRICES` stays as the fallback row for a model the file does not have.
- Budgets: `DEMO_COST_DAY` in total (5) and `DEMO_COST_CHOICES="haiku=3,luna=2"`. Before a run:
  - the total is used up: 429 `reason: cost`, as today;
  - the run's choice is used up and it is a new conversation: the other choice answers, and the run carries `CUSTOM notice` `{text: "Luna's demo budget for today is used up; Haiku answers.", code: "model_fallback", choice}` after the `model` event;
  - the run's choice is used up and the conversation exists: 429 `{code: "demo_limit", reason: "model_cost", choice, other}`; the page offers a new conversation on the other choice.
- Visitor, IP, thread and site limits stay shared between the choices.

## Ask AI

`docs_ai.app.create_app(models={name: model})`; the host passes its choices. `forwardedProps.model` picks one per question; the history is plain text, so the choice may change in the middle of a conversation. The same `model` event, the same budgets.

## Tests

Offline with scripted models, one per choice: the right model answers each role; an unknown name and an unusable choice are refused; a thread keeps its model (409) and a run without a name follows the thread; Dushes' own turn, its router and the researcher follow the choice; the `model` event; `KEYS`. Host: prices per model with the tier, both budgets, the fallback notice on a new conversation, the 429 on an existing one, `/agent/models`. Ask AI: a choice per question.
QA: scenarios for the rules above and a live smoke on both models (agent only, a few cents).

## Not in this change

- A free-form model id from a request, at any level.
- Changing the model of an existing form or site conversation.
- The switch itself and the "answered by" line (widget designer).
