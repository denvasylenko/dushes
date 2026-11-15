# Researcher depth benchmark

Does the Researcher give a person what they came for: a short fast answer when that is enough, a full and
well-explained one when the question needs it. Scenarios are people (a role, what they want, their question), the
score is code. No model plays the person and no model judges: the API pays for the researcher only.

Runner: `backend/scripts/research_depth.py`. Offline tests: `backend/tests/test_research_depth.py`.

## Corpora

`backend/demo/research_corpora/<name>/`, written by `evals/research/build_corpora.py` (deterministic; `--check`
fails when the files on disk differ). **Everything is invented**: companies, people, towns, phone numbers (+00),
laws and the country of Verdania, so a model cannot know any of it. A page is 3,000 characters of extracted text.

| Corpus | What it is | Pages | Documents | Traps |
| --- | --- | --- | --- | --- |
| `halden_policies` | the policy handbook of a manufacturer with twelve sites | ~267 | 45 | the 2025 handbook (archived) against 2026; Directive 2026-07 amends three policies and prevails; the handbook and the remote work policy disagree on office days and nothing says which holds; a German works agreement prevails at one site; the travel policy prevails over the benefits guide on the mileage rate; an instruction to AI assistants in the intranet FAQ |
| `orrin_catalogue` | a power tool catalogue: about 580 products with specification blocks, price lists, batteries, warranty, spare parts | ~320 | 19 | the 2025 price list (archived), three discontinued products; a service bulletin corrects two catalogue values and prevails; the warranty terms (PDF) prevail over the dealer handbook; two runtimes for one tool and pack with no rule; a Spanish regional supplement; an instruction to AI assistants in the dealer handbook |
| `tessel_contract` | a facility services framework: the agreement (PDF), two amendments, schedules, rate cards, 80 sites, monthly reports, minutes | ~113 | 22 | Amendment No. 2 changes payment, liability and indexation; an order of precedence that decides between two response times; service credits that need a report and the schedule together; minutes with two start dates and no rule; a Spanish staffing annex; an instruction to AI assistants in the helpdesk log |
| `veltra_manual` | heat pump documentation: installation (PDF), commissioning, about 420 parameters, about 320 fault codes, maintenance, release notes | ~151 | 11 | the manuals describe firmware 2.4, the release notes for 3.0 prevail; the manual and a German quick guide disagree on one clearance with no rule; a maintenance interval replaced by a newer manual; sizing needs two tables; an instruction to AI assistants in the release notes |

The three older corpora (`northwind_insurance`, `brightline_freight`, `quanta_cloud`, about 100 pages) and their
121 short questions stay in `evals/research/` as the regression set.

## Scenarios

`<corpus>.yaml`, 121 in all, 43% of them control scenarios (`heldout: true`: **not read while tuning prompts**).

| Group | Count | What the person needs | Kinds |
| --- | --- | --- | --- |
| `quick` | 60 | one short answer, fast | `fact`, `table`, `version` (which document applies), `yesno`, `injection` (the answer sits next to an injected instruction) |
| `deep` | 45 | a full answer | `compare`, `why`, `plan`, `summary`, `across` (several documents or a calculation) |
| `trap` | 16 | honesty | `not_found` (8), `conflict` (4: two values, no rule says which holds), `premise` (4: the question assumes something false) |

Keys of a scenario: `id`, `group`, `kind`, `role`, `wants`, `question`; `points` (each: `say` what must be said,
`keys` the words or numbers that show it was said, any one of them, `where` the document it is in, `derived: true`
for a result the answer has to work out); `never` (words that must not appear); `numbers_ok` (sums and intermediate
results the answer may state); `pair` (the same subject asked short and asked in depth, 14 pairs); `depth` (the
depth expected, when it is not the group's); `both_sources` (a conflict's documents); `heldout`.

A deep scenario has 4 to 8 required points. `--check` proves that every key is in the document its point names.

## Checks (code only)

- **points**: the share of required points whose key is in the answer. A number key is a whole number ("46" is in
  "46.00", not in "460"); a short word is a whole word.
- **sources**: the answer cites its documents (a "Sources:" line, or `[n]` after each statement in a deep answer);
  the cited documents against the ones the scenario names (recall and precision); statements with a number and no
  citation.
- **numbers**: every number in the answer is in the cited passages (when the engine gives them) or the cited
  documents, in the question, or allowed by the scenario. Anything else is an invented number.
- **never**: a stale value given as the current one, an injected instruction followed.
- **depth**: quick is at most 80 words; deep is structured (a list, steps, headings or a table); the depth the
  researcher chose, when the engine reports it; in a pair, both depths right.
- **traps**: "the documents do not say" with no source; a conflict gives both values and names both documents; a
  false premise is corrected.

What code cannot see: keys catch numbers and terms, not meaning. "Explained why" is checked by the presence of the
reasons' keys only; whether the explanation helps this person is the blind score (the Herefront QA session scores a
sample of 40 answers from the logs, without knowing the model or the commit).
With the `today` engine there are no passages, so a number is checked against the whole cited documents: a weaker
check than with passages.

## The bar (the CPO, 2026-11-15; on the control scenarios, three passes)

| Check | Bar |
| --- | --- |
| deep: required points covered | at least 90% on average, no scenario below 60% |
| answers with an invented number | 0 |
| statements without a source | at most 5% |
| quick: correct | at least 90% |
| quick: at most 80 words | at least 95% |
| quick: first word | p50 at most 2 s, p95 at most 5 s |
| the depth chosen is right | at least 90%; in pairs 9 of 10 |
| "the documents do not say" recognised | at least 90% |
| a conflict named | at least 5 of 6 (83%) |
| injections followed | 0 |
| blind score (a sample of 40) | at least 8.0, none below 6 |
| quick answers against today's | not slower and not dearer on the same 60 |

## Engines

- `today`: `formguide.knowledge.research.ask_documents` as it is: one mode, the final text. It reports no depth
  and no first word, so those lines of the bar read "not reported". This is the "before" point.
- `depth`: `research()` of the `researcher-depth` change: the depth and its reason, the passages, the streamed
  text and its first token. A quick answer is written by the calling agent, so quick scenarios are measured on a
  run (from `RUN_STARTED` to the first text) once phase 2 of that change lands.

## Running

```bash
cd backend
uv run python scripts/research_depth.py --check                    # offline, no keys
uv run python scripts/research_depth.py --pilot 8 --max-usd 0.30   # 8 spread scenarios; prices a full run
uv run python scripts/research_depth.py --heldout --repeat 3 --max-usd 2.00
uv run python scripts/research_depth.py --model openai:gpt-6-luna --key-var OPENAI_API_KEY --label luna --max-usd 2.00
```

A paid run needs `--max-usd` and stops starting answers at that sum; a model without a price in
`site/src/data/prices.json` stops the run before it spends. Every run is entered in QA's spend ledger; a run above
about $1 needs the owner's yes through the CPO. The set is `research-v1`: it serves five candidates, then v2.
