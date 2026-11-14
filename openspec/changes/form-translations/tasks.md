# Tasks

- [ ] agree the keys with the widget designer and Docs Lead (connect-your-form)
- [x] read `i18n` and option `names`; show the languages in field cards
- [x] `language` on ask_user and propose_changes; labels and options from the form first; the card carries `language`
- [ ] tests; docs; QA scenario (the form's own Russian labels win over the agent's)
- [x] `CUSTOM language {lang}` per run (message check, else the agent's `language`), kept per thread and in restore; the widget's side by the designer
- [x] formguide/language.py: detect the conversation's language; per thread; the agent's `language` overrides
- [x] check every card before it is sent: form translation first, else one batched, cached translation call; values untouched; a failure never blocks the card
- [x] `language` / `languages` on the host config and on a form; `translate_missing` (default true); detection only when no language is set; config KEYS and the reference
- [ ] still open: the form's languages shown in field cards; Dushes' own turns (pages without a form); the widget's side (designer); docs (Docs Lead); QA's scenarios
