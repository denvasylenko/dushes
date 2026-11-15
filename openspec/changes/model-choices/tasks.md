# Tasks

## 1. Package
- [x] 1.1 `models.choices` in the loader and in KEYS; `GuideConfig.model_choices`; every choice's models built at start; `usable`
- [x] 1.2 the run's choice: `run(model=)`, `forwardedProps.model`, the context variable behind `guide.models`, `suggestions_model`, `translation_model`
- [x] 1.3 a thread keeps its model: the transcript's `model` entry, 409 `model_fixed`, a run without a name follows the thread
- [x] 1.4 Dushes: `run(model=)`, its own turn, the router and the researcher on the choice; form threads follow the site thread
- [x] 1.5 `CUSTOM model` after RUN_STARTED; `FormGuide.model_choices()`; `GET <prefix>/models` in the router
- [x] 1.6 offline tests

## 2. Demo host
- [x] 2.1 the two choices in formguide.hosted.yaml; `GET /agent/models` with `left`
- [x] 2.2 prices per model from prices.json (with the `over` tier), `DEMO_PRICES` as the fallback row
- [x] 2.3 `DEMO_COST_CHOICES`, the total, the fallback notice, the 429 `model_cost`
- [x] 2.4 offline tests

## 3. Ask AI
- [x] 3.1 choices by name, a choice per question, the `model` event
- [x] 3.2 offline tests

## 4. Around it
- [ ] 4.1 the switch and "answered by" in the widget and the demo pages (widget designer)
- [ ] 4.2 the image carries site/src/data/prices.json; the OPENAI_API_KEY secret command (SRE)
- [ ] 4.3 docs: models and choices, the event, the 409 and 422, the demo's budgets (Docs Lead)
- [ ] 4.4 QA: scenarios and the live smoke on both models
- [ ] 4.5 archive: sync `model-configuration` and `docs-assistant`
- [x] 4.6 the SQLite checkpointer's worker thread is a daemon: it kept a process from exiting (found while testing the host)
