# Proposal

## Why

The owner (15.11, through the CPO): "it is unclear what is happening here at all", with three screenshots: a hook with no reference (`useFormguide`, `onReveal`), a guide that is one paragraph of jargon (Hand-off), and a button that seems to do nothing (the theme playground's Reset). And the rule he set: he should not be the one who finds the flaws. The bar is the best developer documentation: open any page and understand it at once.

The three pages are fixed (d3398e5). They were examples of one cause: the site has no rule that every public name has a reference row, no fixed shape for a guide, and no measurement of whether a reader with no context can do the task. This change adds all three, and a structure that follows the reader, not the teams that wrote the parts.

## What Changes

- **A reference for everything public, checked by the build.** Every hook, component, option, method, event and configuration key gets a row: type, default, one sentence on what it is for. Rows for the widget come from its TypeScript types, rows for the server from the Python signatures; a public name without a row fails CI. Every name in a code example links to its row.
- **One shape for a guide.** What it is and when you need it (one plain sentence) → a picture → the minimal example → each line explained → what you see → common mistakes → next. Jargon only as a link to the glossary. A check fails a guide that misses a part.
- **A site map by the reader's journey.** Get started → Build (how-to guides by task) → Concepts → Reference, as react.dev, Next.js and LangChain do; one name for each thing; Install and Quickstart on the first level; the design system leaves the reader's reference.
- **A docs benchmark.** Ten developer tasks; a reader with no context (a subagent that sees only the built site) does each; code checks score the answer. Done means 9 of 10 with no hints, measured before and after.

## Impact

Every guide page is rewritten in the order people read them (about 30 pages); URLs that move get redirects. The widget's and the server's public types become the source of the reference. No change to the product's behaviour.
