## Mini-brief (ui-craft)

1. **Who and why.** A developer evaluating or integrating Dushes; a lazy reader who wants the shortest path to working code or to one fact.
2. **Main action.** Per page: the copyable example (guides) or the fact (reference). Site-wide: search.
3. **Tap ladder.** Today: guess the section (Backend? Your form? Concepts?), scroll a long sidebar. After: pick one of four tabs, or ⌘K and type; a reference fact is one hop from any guide.
4. **States.** Search: empty (recent and suggested pages), no results ("Ask AI: '…'"), loading (instant from the local index). Old links: redirect, never a 404.
5. **Phone.** Tabs become a segmented row under the header (or the first level of the menu); search opens full screen; sidebars collapse as today.

## Information architecture and URL map

| Tab | Section | New path | Old path(s) |
| --- | --- | --- | --- |
| Get started | Overview | `/get-started/` | `/getting-started/overview/` |
| | Quickstart | `/get-started/quickstart/` | `/getting-started/quick-start/` |
| | Live demo | `/get-started/live-demo/` | `/getting-started/demo-app/` (merged) |
| | Benchmarks | `/get-started/benchmarks/` | `/getting-started/benchmarks/` |
| | Open standards | `/get-started/open-standards/` | `/built-on/*` (4 pages folded) |
| Frontend | Choose a client | `/frontend/` | `/frontend/overview/` |
| | Clients | `/frontend/{widget,react,react-hook-form,copilotkit,ag-ui,plain-html}/` | `/frontend/chat-widget/`, `/frontend/agui-client/`, others same name |
| | Connect your form | `/frontend/connect-your-form/{,contract,skeleton,state,value-formats,components,troubleshooting}/` | `/form/*` |
| | Cards and UI | `/frontend/{cards,blocks,card-gallery,themes,frontend-tools,dushes-in-the-page,playground}/` | same names; `/frontend/dushes/` → `dushes-in-the-page` |
| Agents | How it works | `/agents/how-it-works/{,turn,context,knowledge,memory,attachments,architecture}/` | `/concepts/*` |
| | UI agent (FormGuide) | `/agents/ui-agent/{,domain-packs,prefill,skills,cards-from-blocks,user-documents,document-researcher}/` | `/backend/{domain-packs,prefill,skills,cards}/`, `/concepts/attachments/` (guide part) |
| | Site agent (Dushes) | `/agents/site-agent/{,site-map,navigation,hand-off}/`, later `{proactive-tips,user-profile,page-context,host-actions,change-history}/` as those changes ship | `/backend/dushes/` (split) |
| | Shared | `/agents/shared/{install,configuration,models,business-documents,persistence,deploy,observability}/` | `/backend/{install,configuration,models,knowledge,persistence,deploy,observability}/` |
| Reference | Python | `/reference/python/<class>/` (generated) | `/reference/python-api/` |
| | Widget | `/reference/agui-chat/` (generated: attributes, properties, events, parts, CSS variables) | `/reference/agui-chat/` |
| | Contracts | `/reference/{http-api,agui-events,card-payloads,form-types}/` | same; `form-types` from `/form/contract/` types |
| | Configuration, CLI, Specs, Design system | `/reference/{configuration,cli,specifications,design-system}/` | `/reference/*`, `/specifications/*` |

Every old path in the table is a key in `redirects` (Astro static redirects; on the Fly host they are pages with a meta refresh and a canonical link, which also works on GitHub Pages).

## Decisions

- **Tabs**: Starlight's sidebar per tab via the `starlight-sidebar-topics` plugin (one sidebar per topic; the topics as header tabs, see the decision updates below). Alternative: a custom header with links and a filtered sidebar override; chosen only if the plugin cannot be themed to the design system.
- **Generated reference**:
  - Python: a build step (`site/scripts/pyref.mjs` calling a small Python script with `griffe` or `inspect`) reads the public API (`formguide.__all__`, `formguide.site.__all__`, config dataclasses) and writes one MDX page per class into `site/src/content/docs/reference/python/` (generated, not committed, like the specs). Docstrings stay the source; missing parameter docs fail the build in CI (a warning locally).
  - Widget: `packages/agui-chat` publishes `custom-elements.json` (Custom Elements Manifest, generated from `ATTRS`, `ChatOptions`, the events and `TOKENS`); the site renders it. Owned by the widget designer.
- **No duplicated text**: shared mechanics (configuration, models, documents, persistence) live under Agents → Shared; the agent pages link to them.
- **Naming**: section and page titles read "Site agent (Dushes)" and "UI agent (FormGuide)"; the researcher gets its own page under the UI agent (it answers from business documents for the UI agent's `ask_documents`).
- **Phases**: (1) IA, moves, redirects, header tabs; (2) Spotlight search; (3) generated reference. Ask AI on the site agent is a separate later change behind a flag.

## Decision update: one topic switcher

The topics are a source list at the top of the sidebar (`SourceList` in `site/src/components/ui/`, rendered by `site/src/components/Sidebar.astro` over the plugin's current topic), and one segmented row in the phone menu. No header tabs: they would be a second "you are here" next to the source list and the current page row.

## Decision update: names

The form agent is the **UI agent**: it fills and changes any state on the current screen, a form being one case. Until the class rename (`UIAgent`, with `FormGuide` as a deprecated alias) lands, pages write "UI agent (`FormGuide`)". The document researcher is the **Researcher**, a generic deep sub-agent (documents today, data later), at `/agents/researcher/`. The site agent (Dushes) keeps its name.

## Decision update: header tabs (supersedes "one topic switcher")

The owner asked for tabs in the header, as in LangChain Docs; the "one topic switcher" update above replaced them with a sidebar source list without asking the owner, and is withdrawn. The header row holds the logo, search, Ask AI and GitHub; a second row under it holds the tabs Get started · Frontend · Agents · Reference, the active one underlined. The sidebar shows only the current tab's pages, with no topic list at its top. On phones the tabs stay a segmented row in the menu. Tab and sidebar row are two levels of one hierarchy (section, page), as at LangChain, Stripe and Apple Developer. Styling: the docs design-system session.

A change to something the owner asked for explicitly goes to the owner (or the CTO) first, with its reasons; it is not decided in a decision update.
