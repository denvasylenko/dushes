# Proposal

## Why

The owner (through the CPO, 2026-11-15): the Researcher must be quick by default and, when the question needs it, do a deep analysis and give a full, well-explained answer; all of it tested.

Today there is one mode. `ask_documents` starts a free-running deep agent (`deepagents`) for every question: several model calls before anything comes back, an answer capped at about 120 words, and the calling agent then retells it in one to four sentences. A simple "what is the fee?" pays for a research loop; a "compare the two tariffs and tell me why one is dearer" gets the same 120 words. Retrieval is a BM25 pass that re-tokenizes every section on every query, over sections cut at 1200 characters with no overlap, no page numbers and no heading path: fine for ten pages, not for a 300-page handbook next to five other documents.

## What Changes

- **A depth per question**: `researcher.depth: auto | quick | deep` (default `auto`). In `auto` the code decides, from the person's own message and a retrieval probe, never the model and never a prompt line.
- **Quick**: one retrieval in code, no research loop. The calling agent gets the ranked passages with their sources and answers in its own turn. Target: first word in about 2 s.
- **Deep**: a pipeline in code with a model at three points: plan sub-questions, read what each retrieval found, write the synthesis. The answer is structured (the short answer first, then sections), every claim carries a citation, and what the documents do not say is said. It has its own time and cost limit, reports its progress to the chat and can be stopped.
- **The deep answer reaches the person as written**: it is streamed as the assistant's message, not handed to the calling agent to shorten.
- **Retrieval for large documents**: sections that keep their heading path and page, overlap between neighbours, a prebuilt index (no per-query tokenizing), ranking that mixes lexical score, heading match and, when the host configured embeddings, vectors; results spread across documents; neighbours read on demand; a document outline for planning. Works on 100 to 500-page documents and a mixed set of them.
- **Tests**: deterministic tests for the depth decision, chunking, ranking and the pipeline with a scripted model; a retrieval benchmark on generated large documents with known answers; QA's benchmark for answers (built in parallel).

## Capabilities

- `document-research` (modified): depth, quick and deep modes, limits, progress, stop, citations.
- `knowledge-base` (modified): sections for large documents, the index, ranking, the outline.

## Impact

- `backend/formguide/knowledge/` (store, index, research), the `ask_documents` tool of the form agent and of Dushes, `config.py` (`researcher:` keys, in `KEYS` and the reference), `stats.py` (kind `researcher` per phase).
- Stored `chunks.json` gets new fields; documents are re-chunked on start when the stored format is older (no re-upload).
- The widget shows a "researching" status with a stop control: a request to the design team; today's step rows already show `docs.*` steps.
- `deepagents` stays as the engine only for `toolset: data` (core-and-capabilities); the documents toolset no longer needs it, so `formguide[research]` becomes optional for document questions.
- Docs: the Researcher pages (overview, configuration), the events reference, benchmarks (Docs Lead).
- Behaviour of an agent changes: the owner's yes through the CPO and QA scenarios that fail first, per phase.
