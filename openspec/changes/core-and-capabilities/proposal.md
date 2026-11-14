# Proposal

## Why

Dushes cannot exist without a form agent: `Dushes(form_guide, site)` takes knowledge, models, transcripts and attachments from inside `FormGuide`. A site that only needs answers and navigation still builds a form agent, and every new ability (proactive tips, host actions, data questions) has to be bolted onto one of the two agents. The owner decided (14.11, through the CTO) to name the parts after what they do, to put the shared parts in a core that capabilities plug into, and to make a form declared on the server an official mode. The rename is cheapest now, while the Herefront cabinet is the only consumer.

## What Changes

- **Names.** The product is Dushes. Inside it: the **Site agent** (`Dushes`: knows and shows the whole site), the **UI agent** (`FormGuide` → `UIAgent`: fills and changes any state on the current screen; settings, filters, a profile, a booking, a cart are all forms) and the **Researcher** (see below). `FormGuide`, `SiteGuide` and the old module paths stay as deprecated aliases for two minor versions (0.4, 0.5), with a warning on import.
- **A core and capabilities.** `Core` owns the knowledge base, models, conversation memory, transcripts, attachments and transcription. Capabilities are switched on in config and plug into the core: **Know** (knowledge, the Researcher), **Show** (site map, navigation, highlight), **Fill** (the UI agent), **Do** (host actions, each with Undo or a confirm card), **Analyze** (data tools, chart and table cards). A knowledge-only site configures Know + Show and builds no UI agent. `Dushes(core, site_map, ...)` and `UIAgent(core, ...)`; `Dushes(form_guide, site)` keeps working.
- **Declared forms.** A form declared on the server (no form on the page; the chat asks for the fields as cards) becomes an official mode: steps and groups asked in order, any value accepted at any time, a conditional field asked only after its condition holds. Dependent options come from the declaration (small, stable lists) or from an `options(field, values, query)` resolver (large or live lists). When a parent changes: visibility and required are recomputed, options refreshed, still-valid values kept silently, invalid ones cleared with a note and a Restore action. The form or the server decides validity, never the model. A long declared form opens a sheet with its fields next to the chat.
- **The Researcher.** The document researcher becomes a generic Researcher: an isolated sub-agent that reads a lot and returns briefly, with toolsets. `documents` is today's; `data` (later, opt-in) runs SQL or pandas in a sandbox over data the host's tools return with the user's rights, never a direct database connection.
- **A submit guard in code.** A tool marked as submitting is unavailable until the form's review passes (no missing required fields, the server accepted the values), and it runs only when the user taps the summary card's button: a typed "yes" never submits.

## Capabilities

- `core-capabilities` (new): the core, the five capabilities, the names and the aliases.
- `declared-forms` (new): the declared mode, its flow, dependencies and the sheet.
- `researcher` (new; replaces `document-research` as the home of the researcher): toolsets, the data toolset's limits.
- `submit-guard` (new): the guard in code.
- Modified on archive: `dushes`, `document-research`, `action-confirmations`, `model-configuration` (the config's new shape).

## Impact

The cabinet keeps working through the aliases and gets a migration note. The docs move to the new names (Docs Lead, labels from the CTO). The widget gets the sheet for long declared forms (UI/UX). Phases are in tasks.md; each phase ships on its own with QA's evals and the held-out domain.
