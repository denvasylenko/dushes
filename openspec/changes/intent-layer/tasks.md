# Tasks

Nothing in section 2 or later starts before the QA Lead's measurement of the choosers (D-29) is reported to the
CPO. No supplier's client is written before the owner's yes to that supplier by name.

## 1. Specified
- [x] 1.1 The contract, the generated questions, the settings, the data rules (this change)
- [ ] 1.2 The QA Lead's measurement: rules against Haiku, and the external chooser when the owner has access (synthetic phrases)

## 2. The layer, with rules only
- [ ] 2.1 `formguide.intent`: `Option`, `Question`, `Pick`, `Chooser`, the settings (default `off`)
- [ ] 2.2 The question generator from a form's layout and from the site map
- [ ] 2.3 The `rules` chooser (labels and synonyms, number and date words, yes / no)
- [ ] 2.4 The site agent and the form agent ask the layer first; none, late or off goes to the agent unchanged
- [ ] 2.5 The pick is carried out by the existing paths (a site directive, a quiet field change, a card's answer)
- [ ] 2.6 `never_send`, and a test that no guest's name or phone reaches a chooser
- [ ] 2.7 Offline tests; the QA Lead's scenarios for groups 1 to 4

## 3. After the measurement and the owner's yes
- [ ] 3.1 The external chooser's client behind `Chooser` (one module; its name nowhere else)
- [ ] 3.2 Its calls in the run's stats with time and cost
- [ ] 3.3 `embed`, if the owner agrees to the dependency

## 4. Later, not in this change
- [ ] 4.1 Group 5: suggestions with search, trimming the context, checking an answer, guests' requests
