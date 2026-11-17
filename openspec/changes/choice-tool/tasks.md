# Tasks

Code only after this change is accepted and the QA Lead's measurement plan is priced and agreed. A paid run
starts only after its price went to the CPO and the owner's yes came back.

## 1. Specified
- [x] 1.1 The tool's contract, the two thresholds, what goes to the front end, how the model learns "done", the hand-back answers (design.md)
- [x] 1.2 What the voice provider allows, and the two shapes for voice (design.md)
- [x] 1.2a The hybrid (the owner's correction): a direct command to the layer, the rest to the model with the tool; who decides "direct"
- [x] 1.3 An architect's review (review.md: rework), and the rework of the design and the spec
- [ ] 1.4 The QA Lead's measurement plan: the hybrid against the tool only and the layer only, text and voice, with its price

## 2. The tool in text (demo branch first)
- [ ] 2.0 The chooser's ranked answer in `formguide.intent` (the options in order with their confidences)
- [ ] 2.1 `choose_on_screen` for Dushes (screens, parts) and for the form agent (form, values); the options built by the server; not offered when the layer is off; the name reserved
- [ ] 2.2 Act only when the person's own line asks or takes up an offer, at or above the act threshold and clear of the second: the line first, then the event, the turn ends; the form agent's route from the card step to the end
- [ ] 2.3 The other statuses answered to the model; nothing reported done that was not
- [ ] 2.4 The line kept in the conversation as the assistant's message; the chooser's call in the run's stats with a price per call; one retry of the tool a turn
- [ ] 2.5 Offline tests with a mock chooser, one per status

## 3. Voice, shape A (our agent calls the tool on what was heard)
- [ ] 3.1 A plain command through the layer as today; what leans on the conversation to the agent with the tool
- [ ] 3.2 The voice says the line the server wrote

## 4. Measured, then decided
- [ ] 4.1 QA: the hybrid, the tool only, the layer only, and the agent's own tools with no chooser, on the same phrases, text and voice; the act threshold and the verb list from the same run
- [ ] 4.2 The numbers to the owner through the CPO: the hybrid confirmed, or a road alone

## 5. Only on the owner's yes to the model
- [ ] 5.1 Voice, shape B: the tool registered with the provider's Responses model, as a measured experiment
