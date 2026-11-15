# Tasks

Each phase ships on its own, with the owner's yes through the CPO where it changes how an agent behaves, and QA scenarios that fail first.

## 1. Retrieval for large documents (no behaviour change for the agent)
- [ ] 1.1 sections with `path`, `page`, `order`, overlap; tables and lists kept whole; `format` in chunks.json and re-chunking on start
- [ ] 1.2 the prebuilt BM25 postings, stored and loaded; tokens that keep figures and clause numbers
- [ ] 1.3 ranking: text + heading path + title, fusion with a configured vector index, the spread across documents
- [ ] 1.4 the document outline; `kb.outline(scope)`, `kb.neighbours(section_id)`
- [ ] 1.5 offline tests and the retrieval benchmark on generated 100, 300 and 500-page documents; the time budget
- [ ] 1.6 `knowledge.chunk_chars`, `knowledge.chunk_overlap` in KEYS and the reference

## 2. Depth and the quick mode
- [ ] 2.1 `researcher.depth` and the `quick` keys in config, KEYS, the reference
- [ ] 2.2 `decide()`: the word lists per language, the cross-document probe, the large-document rule; its reason in the tool step and run_stats
- [ ] 2.3 quick: passages as the tool result for the form agent and for Dushes; no deepagents import on this path
- [ ] 2.4 offline tests; QA: quick questions (first word, sources, "the documents do not say")

## 3. The deep pipeline
- [ ] 3.1 plan, retrieve, read (parallel), one gap round, write (streamed), check and repair
- [ ] 3.2 limits: seconds, dollars or tokens; the partial answer
- [ ] 3.3 `CUSTOM research` progress events; stop through the run's stop
- [ ] 3.4 the answer as the assistant's message (`source: "researcher"`), the one-line tool result, sources event
- [ ] 3.5 run_stats: kind `researcher` per phase (plan, read, write), with the depth
- [ ] 3.6 offline tests with a scripted model; QA: deep questions (compare, why, plan, summary of a large document, across documents)

## 4. Around it
- [ ] 4.1 the widget's researching status and stop control (request to the design team)
- [ ] 4.2 docs: Researcher overview and configuration, events, architecture diagram, benchmarks page (Docs Lead)
- [ ] 4.3 `formguide[research]` no longer needed for document questions: README, install page, a deprecation note
- [ ] 4.4 archive: sync `document-research` and `knowledge-base`
