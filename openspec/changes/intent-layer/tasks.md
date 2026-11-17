# Tasks

Nothing in section 2 or later starts before the QA Lead's measurement of the choosers (D-29) is reported to the
CPO. No supplier's client is written before the owner's yes to that supplier by name.

## 1. Specified
- [x] 1.1 The contract, the generated questions, the settings, the data rules (this change)
- [x] 1.2 The QA Lead's first measurement (2026-11-17): nobody passes the bar yet; design.md has the numbers
- [ ] 1.3 The QA Lead's next measurement, with the questions adjusted; it sets the threshold

## 2. The layer, with rules only
- [x] 2.1 `formguide.intent`: `Option`, `Question`, `Pick`, `Chooser`, the settings (default `off`)
- [x] 2.2 The question generator from a form's layout and from the site map
- [x] 2.3 The `rules` chooser, for tests only (never a product's provider: 13% confident errors on new phrasings)
- [ ] 2.4 The site agent and the form agent ask the layer first; none, late or off goes to the agent unchanged
- [ ] 2.5 The pick is carried out by the existing paths (a site directive, a quiet field change, a card's answer)
- [x] 2.6 `never_send`, and a test that no guest's name or phone reaches a chooser
- [x] 2.6a The fallback: no pick, low confidence, a late or failed chooser, or off returns None (the agent's turn)
- [ ] 2.7 Offline tests; the QA Lead's scenarios for groups 1 to 4

## 2a. The local demo (branch `demo/jev`, not main; the owner's word through the CPO)
- [x] 2a.1 The external chooser's client, one module, its key from the keychain through the launcher
- [x] 2a.2 The layer in Dushes' run: the QA Lead's measured questions and decision order; the CPO's two code rules
- [x] 2a.3 A value through the form's own card with no model call; a label of who handled each turn
- [x] 2a.4 Hand-back cases 1, 4, 5, 6 with tests; 2, 3, 7, 8 specified (design.md)

## 3. After the measurement and the owner's yes
- [ ] 3.1 The external chooser's client behind `Chooser` (one module; its name nowhere else)
- [ ] 3.2 Its calls in the run's stats with time and cost
- [ ] 3.3 (dropped by the CPO, 2026-11-17: embeddings gave 10% errors on new phrasings, not worth the dependency)

## 4. Later, not in this change
- [ ] 4.1 Group 5: suggestions with search, trimming the context, checking an answer, guests' requests
