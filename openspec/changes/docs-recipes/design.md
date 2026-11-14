# Design

## Mini-brief

- Who: a developer adding Dushes to a real product, looking for "the one like mine".
- Goal: copy a working setup and know how well it works.
- Main action: copy the recipe's files.
- Feel: a cookbook, not a reference: one page, one outcome.
- Done when: every recipe runs in the evals and shows its measured number.

## Recipe page

Title is the goal ("A gift-card skill"). Parts, in order: one-line goal and when to use it; Summary; the files (Tabs: `formguide.yaml`, `SKILL.md`, tool code), included from `backend/demo/recipes/<name>/`; "What happens" (a replayed transcript, the landing demo's player with the recipe's events, or a static transcript); "How well it works" (Metric: runs where the right tool was called / runs, model, date, link to the report; never "always"); Pitfalls (3-5 bullets); live demo link; Next.

## The first recipes

| # | Recipe | Capability | Depends on |
| --- | --- | --- | --- |
| 1 | Knowledge-only site: answers and navigation, no form | Know, Show | core-and-capabilities (today: Dushes over a form agent) |
| 2 | A site with one form and the hand-off | Show, Fill | shipped |
| 3 | A server-declared form with dependent options | Fill | core-and-capabilities (declared forms) |
| 4 | A gift-card skill (`backend/demo/skills/gift_cards`) | skills | shipped |
| 5 | Income proof from an uploaded payslip | Fill, attachments | shipped |
| 6 | A host action with Undo | Do | host-actions |
| 7 | A host action the user finishes on a confirm card | Do | host-actions |
| 8 | Analytics through skills with a chart card | Analyze | shipped charts; data tools in core-and-capabilities |
| 9 | A skill scoped to one form | skills | shipped |
| 10 | Two overlapping skills and how to separate them | skills | shipped |
| 11 | Voice on the server (`dictation: 'server'`, transcription) | widget, core | shipped |
| 12 | The researcher over a policy library | Know | shipped |
| 13 | Prefill from the host's profile data | Fill | shipped |
| 14 | A frontend tool (the browser's locale and time zone) | tools | shipped |
| 15 | Confirm before a side effect (`confirm_action`) | Do | shipped |
| 16 | A form in a messenger, no frontend: a server-declared form in a Telegram-like chat, fields as cards, the web config unchanged | Fill | core-and-capabilities |

Recipes marked shipped come first; the rest are written when their change lands.

## Numbers

QA's eval report gets a `recipes` section: per recipe, runs, runs where the expected tool was called, model, date. The page reads it at build time (`site/src/data/recipes.json`, written by `backend/scripts/eval_summary.py`); a recipe without a report shows "Not measured yet", never a made-up number.

## Decisions

- Group in the Agents tab; no fifth tab (CTO, 14.11).
- Code included from the scenario's files, so the page and the eval cannot drift.

## Pitfalls: the facts (from Owner, 14.11)

Only cases seen in practice, each with its fix. The Pitfalls page is written from these.

1. **A host rule switches a tool off.** In the cabinet the form agent did not call `hand_back` on "how many new requests?", because the host's domain rule said "tell them where it is". Host instructions rank above the defaults, so they can disable a tool by accident. Fix: host rules must not contradict the tools ("not about the fields: `hand_back` at once").
2. **A display-only tool next to the answer duplicates it.** The site agent wrote the answer and called `suggest_next` (or `navigate`) in the same step; the loop went back to the model and it repeated the answer. Fix in code: after a step with only display tools and finished text, the model is not called again (b888715, b8232d4).
3. **Text where a card belongs.** The agent asked for several values in prose and listed required fields as text instead of showing them. Fix: "several values: one card"; `focus_field` with `fields` highlights several at once.
4. **Large tool outputs flood the context.** The full form config is about 16.7k tokens; the agent sees about 1.2k (outline, the open section, changes) and fetches details through `get_fields` and `search_fields`. The researcher reads in its own context and returns a short answer.
5. **Garbage in sources.** The researcher put file paths and ids in its sources line, which became chips. Fix: sources are resolved against the real documents and anything that matches none is dropped (9f74e6d).
6. **Prompt injection through data.** Field values, documents, site passages and user-submitted texts are data, never instructions: a rule in both prompts and an injection eval scenario.
7. **Side effects without confirmation.** Anything that submits, sends, pays or cancels goes through `confirm_action`; `confirm_tools` in the config forces it. core-and-capabilities adds a code guard (the submit tool is unavailable until review and runs only on the card's tap).
8. **Word forms miss the router.** The router matched site map words only whole; in Russian and Italian a plural and a singular form differ, so a question went to the wrong agent. Fix: stems, the router model for unclear cases, `hand_back` / `to_form` as a safety net.
9. **A demo example in a generic prompt.** Loan and bank-branch examples tilted the model toward the demo. Fix: neutral examples and a held-out domain in the evals (car insurance scored 8.8 with no tuning).
10. **An inline domain pack is server-wide per `form_id`.** One test chat that registered a layout with a different domain changed the pack for everyone until a restart. Still true (formguide/domain/packs.py, `register` ahead of every source). Page wording: "in production, don't send `domain` with the form from an untrusted client: keep packs in the server config (`domain_packs`)". A fix (per-thread or per-`jsx_hash` inline packs, or a config switch) is proposed to the owner; if it lands first, the page cites its commit.
11. **The model computes numbers.** It applied a discount to the wrong product and computed payments. Fix: a rule in both agents to quote conditions, not compute amounts and rates; the form computes, the agent reads the computed field.

Not included: tool-count limits of strict grammars (not seen in practice).

## Recipe folders (QA, 14.11)

Runner `backend/scripts/recipes.py` (scripted user, deterministic tool checks, no judge); scenarios `backend/evals/recipes/recipe_*.yaml`, a recipe's number is the sum over its scenarios. Each recipe runs in-process from `backend/demo/recipes/<name>/`; tool modules sit at the folder root as `<recipe>_tools.py` and are referenced as `"gift_card_tools:check_gift_card"`, because the folder is on `sys.path`. Every page with a tool module says so in one line. Negative checks (a skill that must not fire on another form, a refund tool that must not run on a balance question) count as hits when the tool is not called.

`site/src/data/recipes.json` entries: `{runs, hits, scenarios, tool, model, date, report}`; `runs` and `hits` are summed over the recipe's scenarios, `tool` joins each scenario's expectation with "; ". The page reads "19 of 20 runs (2 scenarios)".
