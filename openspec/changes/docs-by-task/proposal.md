# Proposal

## Why

The owner (14.11, through the CTO): "the docs are hard to use; make them much more convenient: more examples, more configurations, and the many options grouped and presented properly so there is no information noise." Two audits agree (Head of Growth's, and a ux-auditor walk at 1280 and 390 px): the live demo and Ask AI convince, but the written path to a first chat breaks at the widget script (not on npm; the site serves it only at an unlinked `/widget/agui-chat.iife.js`), the quickstart's frontend snippets do not run as written, a non-React form has no path, configuration is grouped by file (one 9,100 px page, 18 stacked code blocks, no tabs), server and page halves of one task (voice, attachments) are never shown together, no page gives a dollar cost per turn, and one reader meets seven names.

## What Changes

- **Configure, by task.** A new "Configure" group in the Agents tab, one page per task: Connect a model, Your form, Add your documents, Look and feel, Voice, Attachments, Limits and cost, History and memory, Deploy. Each page: a one-line promise, an example first (variants as tabs), a "Most people need" table of 3–5 options with defaults, both sides when a task has a server and a page half, "Every option" collapsed, Next cards. The 7-step "Build it up" page and the repeated Azure and every-key blocks go away; their content moves into the groups.
- **One lookup table.** Reference → Configuration becomes one searchable table of every server key and widget option: key or attribute, side (server / page), default, group, link. Widget option table columns fixed and grouped; deprecated names in a footnote.
- **A quickstart that is true.** One self-contained `index.html` that runs when pasted, with the script's absolute URL until the widget is on npm, and HTML / React / react-hook-form / Vue tabs. "Build from source" in a disclosure. Every page that imports the package says how to get it.
- **A form without a backend.** A page for any framework with `schemaForm` (needs the widget team to export it from the one-script build), linked first from "Choose a client"; the custom form-backend contract becomes the advanced path.
- **Cost per turn in dollars**, computed at build time from the benchmark report and the model's price (a dated data file, never typed), and the landing's token metric relabelled as the form's share of the prompt.
- **Less noise:** the example before the explanation, short paragraphs, the glossary as links, "your form's server (any language)" instead of Java, one sentence on names on the overview and in the footer, the CLI page saying `formguide`.
- **Landing order:** the live demo directly under the hero, setup after it.
- **Search:** each Reference row indexed as its own entry, a boost for `snake_case` and dotted queries, synonyms (turn off, disable, hide).
- **Exports for AI tools:** the `.md` and `llms-full.txt` exports keep JSX lines in code (a build check that code blocks keep their line count).

## Capabilities

- Modified: `docs-site`.

## Impact

- Docs Lead: the pages, the table, the quickstart, the cost data, the landing order, the exports and their check.
- Docs design-system session: the table's filter, tabs and disclosures as needed (primitives exist).
- Widget team: export `schemaForm` from the one-script build; npm publish (Owner's decision).
- Owner: the license choice (Growth's blocker, not docs); `--prices` source for cost.
- QA: `bench.py --site` with prices.
- Out of scope here: analytics beacon (needs the owner's yes), renaming the agents (the owner chose "UI agent").
