## 0. The owner's three pages
- [x] 0.1 `useFormguide` reference, the react-hook-form example line by line; Hand-off in the guide shape; "Restore defaults" (d3398e5)

## 1. Measure
- [x] 1.1 Ten tasks with answer keys and a scoring script (`site/bench/tasks.json`, `scripts/docs_bench.py`)
- [x] 1.2 Baseline on the published site (9b93b4a): 7 of 10; after the first rewrites: 9 of 10 (`site/bench/results/2026-11-15.json`). Keys alone passed 10 of 10 while three readers were guessing, so a pass also needs the reader to be sure (4 or 5 of 5)

## 2. A complete reference
- [x] 2.1 `scripts/check_ts_reference.py` in CI for the hook and the schema types
- [ ] 2.2 The form plugin's options, the chat's options, methods and events, the React component, the exported functions: rows from the types, each checked
- [ ] 2.3 Names in code examples link to their rows

## 3. Names and words
- [ ] 3.1 One name per thing; a glossary; a check for the retired names
- [ ] 3.2 Plain first sentences and descriptions on every page

## 4. The new map
- [ ] 4.1 Get started / Build / Concepts / Reference, with redirects; the design system to Contributing
- [ ] 4.2 The tutorial after the Quickstart

## 5. Guides in the guide shape, in reading order
- [ ] 5.1 Quickstart, Connect a form, Send the form's state, Cards, Themes
- [ ] 5.2 The agent pages; the site pages; Run it
- [ ] 5.3 A check that a guide has its parts

## 6. Check
- [ ] 6.1 Benchmark after 2 and after 5: 9 of 10 with no hints
- [ ] 6.2 ux-auditor at 1280 and 390; build, links, exports, English, drift checks

## 7. Examples, coding agents, Ask AI (the owner, 15.11)
- [x] 7.1 Anatomy and counts (`anatomy.py`): 271 examples, one of them a run file; 4 pages with code have something live
- [x] 7.2a Every example is checked against the real code (`scripts/check_examples.py`, in the tests and CI): 237 of 271 examples (Python, YAML, browser, JSON, shell); it found one broken example (the site map's "Every option" was not valid YAML) and one core defect (a misspelled configuration key loads silently, reported to Owner)
- [ ] 7.2b Examples become included files that are run (a browser example loads without an error; a server example passes `formguide check`); a typed example fails the build
- [ ] 7.3 Every example shows its result and opens in the playground or its recipe folder
- [ ] 7.4 Runnable projects: Vue, site agent with hand-off, form only in the chat
- [ ] 7.5 "Copy for your coding agent" on every guide; task bundles; a drop-in file for a project
- [ ] 7.6 Ask AI on the ten tasks and on undocumented questions (QA's runner); then the changes, through Owner
