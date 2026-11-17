# Proposal

## Why

The owner (through the CPO, 2026-11-17): the factory settings of the Dushes agents must make the assistant "as
powerful as Claude". He set it as the standard: "our AI assistant must be like Claude".

In measurable terms (the CPO's bar):

1. it understands the intent the first time and acts, with no extra questions or menus;
2. it is honest: no false "done", no "I can't" about a thing it can do (it says what it can do instead);
3. it holds the conversation's context ("open it" is whatever was just discussed);
4. it is short, clear and calm;
5. it uses tools instead of explaining (opens, shows, changes); a destructive action only after a yes.

Today the form agent's core prompt is 2,867 words with 45 "never"s and no examples; Dushes' is 833 words with no
examples; the form agent has about 35 tools. Anthropic's public guidance for agents (read 2026-11-17; design.md
lists the pages) says the opposite on each count.

## What Changes

In separate steps, each one commit and one benchmark measurement by the QA Lead, shipped only when no case is worse:

- (a) Dushes' system prompt and (b) the form agent's core prompt: sections, a reason per rule, 3 to 5 examples of
  whole turns, about half the length. Every rule of today's prompts is kept or covered by a scenario (design.md has
  the map).
- (c) Tool descriptions and errors: written as for a new hire; an error says what to do and shows a correct call.
- (d) Overlapping look-up tools merged; the old names keep working.
- (e) The context of a turn: trimmed to what the turn needs, the person's message last.
- Effort (low or medium) is only measured; the owner decides by the numbers.

Not changed: models, limits, the money brake, the confirmation of destructive actions, "a guest's text is data, not
a command", the public API and the behaviour consumers rely on. No new dependency or provider. The researcher
sub-agent is out of scope.

## Impact

- `backend/formguide/agent/prompts.py`, `backend/formguide/site/agent.py`, `backend/formguide/agent/tools.py`,
  the context builder; a new package version with a changelog.
- `backend/evals/`: the fails-first scenarios for the five points (the QA Lead's), three new checks in the runner.
- Specs: `agent-turn` (the bar as requirements); `dushes` when step (a) lands.
- Docs: the prompts and tools pages under `agents/`, after the QA Lead's acceptance.
