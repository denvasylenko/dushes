# Design

## The shape

```
ask_documents(question)                 <- the form agent's tool, Dushes' tool
  depth = decide(config, person's message, question, probe)     # code
  quick: passages = retrieve(question, k)                        # code, no model
         -> tool result: ranked passages + source labels; the calling agent answers
  deep:  plan      -> sub-questions (1 model call, JSON)
         retrieve  -> per sub-question, across documents (code)
         read      -> notes per sub-question with passage ids (1 model call each, in parallel)
         gaps      -> at most one more round for what is still missing (code decides from the notes)
         write     -> the synthesis, streamed to the person (1 model call)
         check     -> every citation resolves, every paragraph has one (code); one repair pass
```

No free-running agent loop for documents: the steps and their order are code, the model fills them in. That is what makes time and cost bounded and the behaviour testable with a scripted model.

## Deciding the depth (`auto`)

Input: the person's own last message (not the agent's rewording), the tool's question, and a retrieval probe (the top 8 hits, which is the quick mode's retrieval anyway, so it costs nothing extra).

Deep when any of these holds:
- the message compares ("compare", "versus", "difference between", "which is better / cheaper"), asks why or how something works, asks for a plan, steps, a summary or an overview, or says "in detail", "thoroughly", "explain fully" (word lists per language, as `\u` escapes for non-English);
- the probe's strong hits come from two or more documents with close scores (the answer spans documents);
- the question asks to summarize a document whose length is over a threshold (`deep.large_document_chars`).

Quick otherwise. A host sets `depth: quick` or `deep` to switch the decision off. The decision and its reason go to the tool step shown in the chat and to `run_stats` (`depth`, `why`), so a wrong call is visible in a transcript.

Not in this change: escalating from quick to deep when quick finds little. Quick says "the documents do not say"; a second, slower attempt behind the person's back would break the 2 s promise. Open question 1.

## Quick

`retrieve(question, k=quick.k)` and return, as the tool result, up to `quick.k` passages: `[n] <document> > <heading path> (p. 12)` and the passage text, cut to `quick.passage_chars`. The calling agent answers under its existing rules and its sources line; `parse_sources` keeps working because labels are the same.
Cost: zero extra model calls. Time: retrieval (under 50 ms on 500 pages, see below) plus the agent's own next call.

## Deep

- **Plan**: one call with the question and the outlines of the documents in scope (titles, heading paths, page ranges; no body text). Output: 2 to `deep.max_subquestions` sub-questions, each with the documents it expects. Invalid JSON: fall back to the question itself as the only sub-question.
- **Retrieve**: per sub-question, top `deep.k`, at most `deep.per_document` from one document, neighbours of a hit pulled in when the hit ends mid-list or mid-table. Passages are deduplicated across sub-questions.
- **Read**: one call per sub-question, in parallel, with its passages: "notes that answer this, each with the passage numbers; say what is not answered". Calls share nothing but the question.
- **Gaps**: code looks at "not answered" notes; when there are any and budget is left, one more retrieve + read with the sub-question reworded by the planner's own alternative wording (asked for in the plan call, so no extra call).
- **Write**: one streamed call with the notes: the short answer first (two or three sentences), then sections with headings, a citation `[n]` after every claim, "The documents do not say …" for each gap, in the person's language. Length follows the question, bounded by `deep.max_words`.
- **Check**: code maps every `[n]` to a passage (unknown numbers are removed), and a paragraph or bullet with no citation and no "do not say" triggers one repair call for that paragraph only. After that an uncited sentence stays out of the answer.

### Limits, progress, stop

- `deep.max_seconds` (default 45) and `deep.max_usd` (default 0.05, from the configured prices; off when prices are unset, then `deep.max_tokens`). When a limit is hit the pipeline goes straight to Write with what it has and says the answer is partial.
- Progress: `CUSTOM research` `{phase: plan | search | read | write, done, total, label}`; the existing tool-step events (`docs.search`, `docs.read`) stay for older clients.
- Stop: the turn's existing stop (`POST /runs/{id}/stop`) cancels the pipeline's tasks; what was written is kept in the transcript marked `stopped`.

### Where the deep answer goes

The synthesis is streamed to the person as an assistant message of the run (role assistant, `source: "researcher"` in the transcript), with its sources event. The calling agent's tool result is one line: "The researcher answered the person directly (N words, M sources). Do not repeat it; add at most one sentence if a form step follows." So the answer is not shortened, not paid for twice, and the history of the calling agent stays small (it holds the short answer part only, for follow-ups).

Alternative considered: return the full text to the agent. Rejected: the agent's reply rules cut it to four sentences, and the tokens are paid twice.

## Retrieval for large documents

- **Sections**: cut on headings first, then on paragraphs to about `chunk_chars` (1200) with `chunk_overlap` (150) characters carried over; a table or a list is not split while it fits twice the size. Each section stores `path` (the heading chain, "4 Fees > 4.2 Late payment"), `page` for PDFs (from the page break, not a fake "Page N" heading), `order` in its document, and `chars`.
- **Index**: BM25 over prebuilt postings (term -> section ids and counts), built when a document is added and kept in memory; a query touches only the postings of its terms. Stored next to `chunks.json` so a restart loads it instead of rebuilding.
- **Ranking**: `score = bm25(text) + w_path * bm25(path) + w_title * match(title)`, then reciprocal-rank fusion with the vector index when the host configured one (`VectorStoreIndex`), then a spread step: no more than `per_document` hits from one document while others have hits within a ratio of the top score.
- **Numbers and codes**: tokens keep digits and separators ("4.2", "27,90", "DE89…") so an exact figure or clause number is findable.
- **Outline**: per document, the heading paths with page ranges and sizes; built in code at upload. No model call at upload in this change (summaries per section are open question 2).
- **Migration**: `chunks.json` carries a `format` number; an older one is re-chunked from the stored text on start.

Expected size: 500 pages is about 1.2 M characters, about 1200 sections; the postings fit in a few MB; a query is under 50 ms on the hosting machine (a test asserts a budget on a generated corpus).

## Configuration

```yaml
researcher:
  depth: auto            # auto | quick | deep
  quick: {k: 6, passage_chars: 900}
  deep:
    max_seconds: 45
    max_usd: 0.05
    max_subquestions: 5
    k: 8
    per_document: 4
    max_words: 600
    large_document_chars: 60000
knowledge:
  chunk_chars: 1200
  chunk_overlap: 150
```

`models.research` stays the model for the deep steps; a host may give `models.research_plan` a cheaper one. Every key goes into `formguide.config.KEYS` and the reference (the docs test fails otherwise).

## Tests

- Offline, no model: the depth decision (a table of messages per language and probes), chunking (overlap, tables, pages, paths), the index (same ranking as the old BM25 on small sets, a time budget on a generated 500-page corpus), the spread step, the outline, migration.
- Offline, scripted model: the deep pipeline end to end (plan, parallel reads, a gap round, the write, the check and its repair), limits (time and cost hit mid-way give a partial answer), stop, the events, the direct answer in the transcript, `run_stats` lines per phase.
- Retrieval benchmark (no model, in CI): generated documents of 100, 300 and 500 pages with planted facts; recall@6 and recall@8 of the planted section per question type (exact figure, paraphrase, cross-document). A bar is set from the first run and may not drop.
- QA's benchmark (agent only, scripted questions, code checks): answer correctness, citation precision, honesty on unanswerable questions, depth chosen, first word and total time, cost per question.

## Open questions

1. Quick finds little: answer "the documents do not say" (proposed), or offer "Look deeper?" as a suggestion chip the person taps.
2. Section summaries at upload (a model call per section, paid once) would make "summarize this 300-page document" better than outline-plus-retrieval. Proposed: later, behind `knowledge.summaries: true`.
3. The default limits (45 s, $0.05) are guesses until QA's first numbers.
