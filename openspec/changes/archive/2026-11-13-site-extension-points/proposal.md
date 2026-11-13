# Proposal

## Why

The site agent was built for a static site: the site map, a few passages, one to three sentences. A host with live data of its own (the Herefront cabinet: the site's facts, statistics, guest requests, connections) had to replace it with an agent of its own, beside formguide. A live run of the cabinet scored 4.8/10 with the stock site agent and 7.9/10 with the host's own extensions. Those extensions belong in formguide, so a host configures the site agent instead of rewriting it.

## What Changes

- **Host context per run**: `SiteGuide(context=fn)`; `fn(ctx)` returns live facts that go into the site agent's prompt on every turn (no search in between). `run(..., host=...)` passes the host's own object (a site, a user) to every callback; `create_site_router(site, host=fn(request))` builds it from the request.
- **Host instructions and style**: `instructions` (text added to the site map's own), `style` (replaces the default "one to three short sentences"), `history` (turns of history, default 6).
- **Host tools**: `tools=[SiteTool(name, description, parameters, handler)]`; `handler(args, ctx)` returns text for the model (sync or async). A failing tool tells the model, never ends the turn.
- **Suggestions**: `suggestions=True` adds a `suggest_next` tool; its options go out as CUSTOM `suggestions {items}` after the answer.
- **Hand-off in the same run**: `form_for(form_id, ctx)` returns the form's state on the server. When it does, `open_form` ends the site agent's turn and the form agent answers right away in the same stream; the directive carries `handoff: "done"` so the page does not run a second time. Without `form_for`, the page's second run stays as today.
- **Language at the hand-off**: `open_form` takes `language`; the form agent is told to reply in it.
- **Routing by who spoke last**: on a form page, when the site agent spoke last, a message without clear navigation words goes to the router model instead of straight to the form. Navigation words in German, Spanish, French, Italian, Russian and Ukrainian go to the router model too.

## Capabilities

- `site-assistant`: the extension points, same-run hand-off, language, routing.
