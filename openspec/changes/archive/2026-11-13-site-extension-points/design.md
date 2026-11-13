# Design

## Shape

```python
SiteGuide(guide, site_map,
          context=fn,          # (ctx) -> str | Awaitable[str]: live facts, in the prompt every turn
          instructions="...",  # added to the site map's instructions
          style="...",         # replaces the default reply length rule
          history=6,           # turns of history the site agent sees
          tools=[SiteTool(...)],
          suggestions=False,   # suggest_next -> CUSTOM suggestions
          form_for=fn)         # (form_id, ctx) -> form state | None | Awaitable: same-run hand-off
site.run(thread_id, message=..., state=..., host=obj)
create_site_router(site, host=fn)   # fn(request) -> obj, per request
```

`ctx` is a `SiteRunCtx(thread_id, page, state, message, host)`. One `SiteGuide` serves every request; whatever differs per request (the site row, the user) arrives as `host`.

## Same-run hand-off

The site agent's loop stops after the round that called `open_form` (no words after it: the form agent answers). `SiteGuide.run` then:
1. emits `site_directive {type: navigate, path, form_id, handoff: "done"}`;
2. runs `FormGuide.run` on the form thread with the hand-off message and the state from `form_for`, dropping its `RUN_STARTED` (the run already started) and the site agent's `RUN_FINISHED`.

The note is not stored as a pending hand-off in that case, so a later page run with `handoff: true` finds nothing and does nothing. The page skips its own hand-off run when the directive says `handoff: "done"`.

## Routing

`route()` on a form page with a typed message:
1. English navigation words → site (as today);
2. navigation words of other languages → unclear;
3. another page's title or keywords → unclear;
4. the site agent spoke last (the last assistant entry of the site transcript has no `form_id`) → unclear;
5. otherwise → form.

Unclear goes to the router model, which now also sees who spoke last and what they said, so a reply to the site agent's question stays with the site agent and a reply to the form agent's stays with the form.

## Not in this change

The npm release of the widget (it waits for the npm organization and a license).
