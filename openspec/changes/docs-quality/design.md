# Design

## What the best documentation does (studied 15.11)

| Site | What it does | What we take |
| --- | --- | --- |
| [react.dev/learn](https://react.dev/learn) | Learn and Reference are two halves. A Learn page opens with "You will learn" (5-6 bullets), then one idea at a time, each with a few lines of code and a runnable sandbox. | "You will learn" at the top of every guide; one idea per section; a result you can see after each example. |
| [react.dev/reference/react/useState](https://react.dev/reference/react/useState) | Every hook page has the same parts: one sentence, the signature, **Reference** (Parameters, Returns, Caveats), **Usage** (sections named by task), **Troubleshooting** (sections named by the symptom: "I've updated the state, but the screen doesn't update"). | The exact shape for every hook, component and function page. Troubleshooting titled by what the reader sees. |
| [LangChain](https://docs.langchain.com/oss/python/langchain/quickstart) / [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) | A short, flat sidebar: Get started (Overview, Install, Quickstart), then Core components named by noun (Agents, Models, Tools, Memory). The overview says what it is, when to use something else, the install line and ten lines of code. Provider tabs on every example. "Copy prompt" for coding assistants. | A first page that says what Dushes is and is not in four sentences, then code. A sidebar a newcomer can read in one look. Provider tabs (we have them). |
| [Next.js](https://nextjs.org/docs/app/getting-started/installation) | Getting Started is a numbered path (Installation, Project Structure, ...), Guides are separate, API Reference is separate. A reference page starts with a table of every prop (prop, example, type, required), then one section per prop with code ([Link](https://nextjs.org/docs/app/api-reference/components/link)). | A numbered learning path after the Quickstart. The prop table with an Example column at the top of each reference page. |
| [Stripe](https://docs.stripe.com/payments/quickstart) | A quickstart is numbered steps with the code beside them, a language picker for frontend and backend, and "Download example". The API reference is by object, with cross-cutting topics first (Authentication, Errors). | Server and page side by side on a task that has both. A downloadable, running example for each guide. Errors as a first-class reference page. |

What they all share, and we lack: a fixed page shape per kind of page, a reference that is complete, troubleshooting by symptom, and one name per thing.

## The audit (69 pages, 40,900 words; measured from the sources on 15.11)

The script is `measure.py` in this folder; the numbers are from it, the reading is mine.

| # | Problem | How bad | Evidence | Fix |
| --- | --- | --- | --- | --- |
| 1 | **Public names without a reference.** The owner's `useFormguide` was one case. | Blocks | The form plugin `formguide({...})` has 16 options and no reference list (they are spread over four guides; `revertChanges` and `baseUrl` are nowhere). `runHttp`, `sseEvents`, `shrinkImage`, `themeCss` are exported and never mentioned. The plugin interface's `beforeRun` and `applySuggestion` are named nowhere. | Generated reference from the types; CI fails on a name without a row (started: 5 types). |
| 2 | **The site follows the teams, not the reader.** | Blocks | Tabs are Frontend / Agents; Install is at Agents › Server and setup; "how to add documents" is under Agents › shared; seven sidebar entries are called "Overview", two "Configuration"; 83 sidebar entries. | The new map below. |
| 3 | **One thing, four names.** | High | The same assistant is "form assistant" (Overview, Quickstart), "UI agent" (Agents), `FormGuide` (code), "form agent" (specs); the product is Dushes, the package `formguide`, the widget `agui-chat`. | One name per thing, said once on the first page and in the glossary; a check for the retired names. |
| 4 | **No "what you will see", no "what goes wrong".** | High | 65 of 69 pages have no result section; 64 of 69 have no mistakes, troubleshooting or limits section. | The guide template; troubleshooting titled by symptom. |
| 5 | **Jargon before meaning.** | High | Page descriptions such as "Each run carries {config, jsx_hash, form_id, ui}" and "Dushes speaks plain AG-UI"; `state`, `http-api`, `contract`, `open-standards`, `persistence` have 3-5 protocol terms in their first 120 words. No glossary. | Plain first sentence; a glossary; terms link to it. |
| 6 | **Walls of text.** | High | Paragraphs of 309 words (Architecture), 265 (Site agent), 233 (The chat widget), 183 (Cards); table cells of 610 and 607 characters (Configuration keys, `<agui-chat>` API). | Reference rows as parameter lists (done for Python); one idea per paragraph. |
| 7 | **Pages that try to be three kinds at once.** | High | The chat widget (3,500 words, 17 sections), Cards (2,900), Architecture (2,800), Speed and tracing (2,100) mix a guide, a concept and a reference. | Split by kind: a guide per task, the concept, the reference rows. |
| 8 | **Few pictures.** | Medium | 44 of 69 pages have no diagram; the six "How it works" pages are only a diagram with no words under it. | A picture on every guide (template); two sentences and "what to read next" under each concept diagram. |
| 9 | **No learning path after the Quickstart.** | Medium | Overview has 241 words before its first code; after the Quickstart the reader gets a list of links, not a next step ("now your own form"). | A tutorial of four steps: your form, the first card, your documents, your look. |
| 10 | **Contributor pages among reader pages; exports with noise.** | Medium | Design system (2,100 words) sits in the reader's Reference; the Agents page's Markdown export carries a raw `export const demoBase ...` line. | Move the design system to a Contributing area; the exporter drops MDX `export` lines and the export check fails on one. |

Good, and kept: the live demo on the first screen, the card gallery, the recipes with measured numbers, the benchmarks from data, Ask AI, the Markdown exports.

## The new site map

Four parts, in the order a reader needs them. Each line is one page; (new) pages are marked.

**1. Get started**: What is Dushes (what it is, what it is not, the three names: Dushes, the UI agent, the chat) · Quickstart (15 minutes) · Install · Tutorial (new; four steps: connect your form, the first card, your documents, your look) · Live demo · Benchmarks

**2. Build** (how-to guides, each in the guide shape)
- *Your form*: Connect a form (HTML, React, react-hook-form, Vue as tabs) · Send the form's state · Value formats · A form without a backend (new) · A form only in the chat · Troubleshooting
- *The chat*: Add the chat to a page · Cards and answers · Your own cards · Themes · Languages · Voice (new, server and page together) · Attachments (new, server and page together) · What the chat can do
- *The agent*: Choose a model · Teach it your form (domain packs) · Business documents · Skills and tools · Confirm before acting · Prefill · The researcher
- *A whole site*: The site agent · Site map · Hand-off to a form · Navigation
- *Run it*: Configuration · History and memory · Limits and cost (new) · Deploy · Test and observe
- *Recipes*

**3. Concepts**: One turn · What the model sees · Memory · Knowledge · Attachments · Architecture · Open standards · Glossary (new)

**4. Reference** (generated, complete): Configuration keys · Python API · `<agui-chat>` (attributes, options, methods, events) · React (`<AguiChat>`, `useFormguide`) · The form plugin (new: `formguide()` options) · Exports (new: `defineTheme`, `runHttp`, ...) · Types and the wire · HTTP API · AG-UI events · CLI · Errors (new) · Specifications

Contributing (outside the reader's path): Design system.

Every moved URL gets a redirect. The tabs become Get started / Build / Concepts / Reference.

## Page shapes

- **Guide**: You will learn (3-5 bullets) → what it is and when you need it (one plain sentence) → a picture → the minimal example → the example line by line, each name linked to its reference row → what you see → common mistakes (by symptom) → next.
- **Reference**: one sentence → the signature → a table of every parameter or option (name, example, type, default) → one entry per name → returns → caveats → usage by task → troubleshooting by symptom.
- **Concept**: the question it answers → a diagram → three to five short paragraphs → what it means for you → next.

## The docs benchmark

Ten tasks a developer brings: connect a react-hook-form form; hand a visitor from the site to a form; change the chat's colours; a tool that asks before it acts; a form only in the chat; answers from our documents; cards in German; Azure with a cheaper model for research; put it on the internet safely; read yesterday's conversations and delete old ones.

A reader with no context (a subagent that is given only the built site's pages) writes the exact code and steps for one task. A key per task lists what a right answer must contain (names, keys, calls); a script scores it, no judge model. A second fresh reader reads each page the first one used and says, per page, whether it understood it at once and what stopped it. Done: 9 of 10 tasks pass with no hints. Runs on the subscription; no API calls.

## Order

1. Benchmark baseline on the published site. 2. Generated reference (the plugin's options first). 3. Glossary and names. 4. The new map with redirects. 5. Guides rewritten in reading order: Quickstart, Connect a form, Cards, Themes, the agent pages, the site pages. 6. Benchmark again after 2 and after 5.

## Anatomy, examples, coding agents, Ask AI (the owner's request of 15.11; `anatomy.py` reproduces the counts)

**Anatomy.** 69 reader pages: 50 guides, 8 concepts, 8 reference pages, 3 recipes. By section: Frontend 23 pages (16 plus 7 under "connect your form"), Agents 32 (shared 8, how it works 7, UI agent 6, site agent 4, researcher 3, recipes 3, overview 1), Get started 5, Reference 8, home 1. More than half of all code (85 of 271 examples) sits in the eight "shared" server pages.

**Examples.** 271 code examples on 49 pages (Python 58, YAML 56, shell 32, JavaScript and TypeScript 57, JSON 19). Exactly one is a file that is run (the Quickstart's HTML); the other 270 are typed into the page and nothing checks that they work. Of the 49 pages with code, 16 have a diagram, 1 a picture and 4 something live; 111 examples are on pages with nothing to look at. There are three runnable example projects (plain HTML, react-hook-form, CopilotKit): none for Vue, the site agent, the hand-off or a form only in the chat. The Playground covers the chat's settings, and no example links into it.

**Coding agents.** One setup prompt (landing and Quickstart); "Copy page", "Open in Claude" and "Open in ChatGPT" on every page; `llms.txt` (121 lines), `<page>.md` and `llms-full.txt` (679 KB, more than many agents can hold). No other guide has a prompt for its task, there is no file an agent can drop into a project (an `AGENTS.md` section or a skill), and no task-sized bundle of pages.

**Ask AI.** It answers in one or two sentences and puts the rest in cards (one code block, steps, pages, a live card), from the six best BM25 passages of `llms-full.txt`. Its measured quality is seven scenarios on two topics (a cheaper research model; showing a card again), all passing. Nothing measures whether it can do the ten developer tasks, whether it says "not documented" when it is not, or how often it shows the wrong block. By design it cannot explain a "why" in more than two sentences or join a server part and a page part except as steps.

### What follows

- **Every example is a file that runs.** Examples move to `site/public/examples/` and `backend/demo/recipes/`, are included into the page, and CI runs them (a browser example loads without an error; a server example passes `formguide check`). A typed example fails the build.
- **Every example shows its result and opens somewhere.** A browser example gets "what you see" (a live preview where the chat can run on the page, a picture where it cannot) and "Open in the playground" with its settings; a server example gets the recorded conversation it produces and its recipe folder.
- **Runnable projects for the missing cases**: Vue, the site agent with a hand-off, a form only in the chat.
- **A prompt on every guide**: "Copy for your coding agent", built like the setup prompt (it asks first, then writes, then checks), plus task bundles (`llms-<task>.txt`), and one file to drop into a project so an agent knows the product's rules.
- **Ask AI is measured by the same ten tasks** as the docs benchmark, with the same keys, and on questions the docs do not answer. Then: longer answers when the question is "why" or "how does it work", both sides of a task in one answer, a link to the reference row of every name it shows, and a record of the questions it could not answer, which become docs work. Changes to how it answers go through Owner with a QA scenario that fails first.
