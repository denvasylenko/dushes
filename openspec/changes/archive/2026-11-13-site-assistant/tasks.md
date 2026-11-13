# Tasks

## 1. Backend

- [x] 1.1 `formguide/site/sitemap.py`: load `site.yaml`, the section index, path / tab / section / form checks
- [x] 1.2 `formguide/site/agent.py`: the site agent loop with search_site, navigate, open_form
- [x] 1.3 `formguide/site/guide.py`: `SiteGuide.run`, the router, the hand-off note, the AG-UI router (`/run`, `/map`)
- [x] 1.4 Demo: `demo/site.yaml` and `demo/site_app.py`, mounted at `/site` in `demo/app.py`

## 2. Demo site

- [x] 2.1 `frontend/site.html` + `src/site/`: hash routes, home, loans with tabs, FAQ with accordions, contacts, two form pages
- [x] 2.2 One chat across the pages: the site plugin (state with page and form, site directives, hand-off run)

## 3. Tests

- [x] 3.1 Offline: routing (no form, form, leaving the form, resume), navigate checks, hand-off note, answers from the map
- [x] 3.2 Live: scenarios across pages in the browser (home → loan form hand-off, FAQ question, tab navigation, form → contacts, back to the form with its values)

## 4. Docs

- [x] 4.1 `site/`: concept page and guide for SiteGuide; validate, English check, tests, builds
