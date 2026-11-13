# Proposal

## Why

formguide guides one form. Hosts also want an assistant for the whole site: answer questions about any page, take the user to the right page, tab or section, and hand over to the form agent when they get to a form. The form agent is a finished product and must stay untouched.

## What Changes

- **`SiteGuide`** (new, `formguide/site/`): one assistant for a site, a graph above the form agent.
  - A **router** picks the mode for each turn: the **form agent** (today's `FormGuide`, called as is, one conversation per form inside the site thread) on a page with a form, the **site agent** elsewhere, and the site agent on a form page when the message is about the site, not the form.
  - The **site agent** is small: `search_site`, `navigate` (page, tab or section; a CUSTOM `site_directive` for the page) and `open_form` (navigate and hand the request to the form agent).
- **Hand-off.** `open_form` keeps a short note of what the user wants. The next run on the form page gives it to the form agent as its first message, so it proposes the first fields without the user repeating themselves.
- **Site map** (`site.yaml`): pages, their sections and tabs, and which form a page holds. It is the source of the site knowledge (a BM25 index over the sections) and of the valid navigation targets.
- **A demo site** (`frontend/site.html`, hash routes): a portal of local businesses with
  - a home page;
  - a loans page with tabs;
  - a FAQ with accordions;
  - contacts;
  - two pages with the existing demo forms (loan application, barber booking).
  One chat goes across all of them.
- An AG-UI endpoint `POST /site/run` and `GET /site/map` in the demo.

## Capabilities

### New Capabilities
- `site-assistant`: the site graph: router, site agent, hand-off to the form agent, site map, the site directive.

## Impact

- New: `backend/formguide/site/` (`guide.py`, `agent.py`, `sitemap.py`), `backend/demo/site.yaml`, `backend/demo/site_app.py`; `frontend/site.html`, `frontend/src/site/`.
- Small additions: `backend/demo/app.py` mounts the site router; `frontend/vite.config.ts` adds the second page.
- Untouched: `FormGuide`, its graph, tools and prompts.
- Docs: a concept page and a guide on `site/`.
