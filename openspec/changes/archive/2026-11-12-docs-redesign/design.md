# Design

## Mini-brief (ui-craft)

1. **Who and why.** A developer integrating formguide: the backend person configuring models and documents, the frontend person putting the chat next to a form.
2. **Main action.** Landing: "Get started". A guide page: copy the next snippet. Ask AI: send the question.
3. **Tap ladder.** Today: a question about a YAML key = search → a 170-line table → read. After: "Ask AI" → type → an answer with the exact snippet and a link (2 steps), or the Configuration guide's step for that key (1 click from the sidebar).
4. **States.** Ask AI: empty (three starter questions), streaming (a "Searching the docs" step), answer with sources, error ("The assistant is unavailable. Try again, or open this page in Claude"), not configured (the button opens Claude / ChatGPT with the page). Copy page: "Copied" for 2 s.
5. **Phone.** Ask AI opens as the widget's full-height panel; page actions wrap onto two lines, and Ask AI is the widget's floating button (the header has no room); code tabs scroll inside their box.

## Decisions

- **Stay on Starlight**; add components rather than switching to a hosted platform.
- **Mermaid** through `astro-mermaid` (client-side render, follows the site theme). Hand-drawn SVGs remain for the concept pages, where the layout matters.
- **Markdown outputs** are Astro endpoints over the docs collection: `/llms.txt` (index), `/llms-full.txt` (all pages), `/<slug>.md` (one page). Concept pages whose body is an HTML fragment get the fragment's text.
- **The docs assistant** is a separate FastAPI app, not a formguide form agent: docs Q&A has no form. It reuses formguide's `BM25Index` for retrieval and `agui.encode` for the wire, so the site's `<agui-chat>` talks to it unchanged. The corpus is `llms-full.txt` from the published site (fetched at start and hourly), or a local file. Per-IP rate limit, a question length cap, CORS to the site's origin, no conversation storage.
- **Model**: any LangChain chat model string, `DOCS_AI_MODEL` (default `anthropic:claude-sonnet-5-5`).
