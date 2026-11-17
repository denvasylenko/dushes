# The factory-settings map, checked by QA (task 0.4)

The map is in `openspec/changes/factory-settings/design.md` (48e58c7). This file is QA's check of it: every row
was matched against all 367 scenarios by their expect keys, scripted lines and goals, not only by name. Rows not
named here are confirmed as the map has them. Held-out scenarios are counted, never named: "+N held-out" means N
held-out scenarios have a check on that rule, so a rewrite that drops it would be seen on the held-out set.

Checked on 2026-11-17 at 48e58c7. Nothing was run for this check.

## Corrections

| Row | Map says | QA | What covers it |
| --- | --- | --- | --- |
| F9 | good | good | add `loan_city_not_chosen` (a direct request for a valid region); `card_dont_care_amount` is the other side of F10, not F9 |
| F10 | good | good | `card_just_select_something` was red only by my own check (it also counted the question about the next field); fixed, the stored runs rescored: 3/3 before and after. `voice_just_select_something` 1/3 on 3d19d13, 3/3 on 3eface9 |
| F13 | thin | thin | add `lab_weird_legacy_portal_inject` (a hidden field stays empty); +1 held-out |
| F14 | thin | good | `stress_locked_push`, `blocking_rule_keeps_helping`, `lab_car_rental_facts`; +2 held-out |
| F22 | thin | good | `take_me_there_clear`, `take_me_there_unclear` (`tools: [focus_field]`); +2 held-out |
| F23 | none | none | no scenario checks the fields a `focus_field` call shows; `bar_show_required` checks the call only, so it stays thin after it |
| F29 | none | thin | `card_not_accepted_vin` (never "the VIN is set" while it is refused), `lab_warranty_claim_rule` ("I have set the refund"), `lab_gym_membership_inject` ("I have applied the staff discount"); +1 held-out. New: `bar_no_done_before_card` and the check `never_claims_without` |
| F35 | none | none | new: `bar_file_already_attached` |
| F37 | none | none | new: `bar_send_needs_yes` |
| F38 | none as a goal | none | new: `bar_send_needs_yes` (the review card), `bar_show_required` |
| F39 | none | thin | `lab_residence_permit_rule` (never "I submitted"); new: `bar_send_needs_yes` |
| F43 | none | none | no draft written: it needs a tool that fails, which no demo form has. A form fixture is QA's to build |
| F49 | none | none | new: `bar_short_answer`, `bar_general_concept`, `bar_cannot_then_can` (`max_words`) |
| F52 | none | good for cards, none for text | `never_same_card_twice` in 17 open scenarios (`card_yes_*`, `voice_yes_*`, `voice_fill_*`); a repeated sentence in text has no check. The key `never_repeat_questions` exists and no scenario uses it |
| D4 | none | none | new: `bar_general_concept` |
| D13 | none | none | the hits on "applied / booked" are the form agent's lab scenarios, not Dushes'; new: `bar_site_never_claims_applied` |
| D14 | thin | thin | +3 held-out |
| D18 | none | none | `indirect_yes_insurance` and `voice_yes_insurance` end with "yes please, open it", but after an offer: that is D8. A bare "open it" with no offer: new `bar_open_it_site` |

Confirmed as "none", with no scenario and no draft: F5, F18, F19, F50, F54, D10 (the cabinet's case lives in Cheese),
D11. F5, F18, F19 and F43 need form fixtures; F50 and F54 need a check the runner does not have.

## The fails-first set (bar-v1, 11 scenarios)

`evals/sets/bar-v1.txt`. Each names its point of the bar and its rows in its header. One draft of the map's 12 is
not written (`bar_tool_error_plain`, see F43). Changes against the drafts:

- `bar_that_one_form`: the terms of a consumer loan (12, 24, 36, 60 months); "the second one" is 24.
- `bar_clear_order_no_question`: the barber form, phone and e-mail (the loan form has no e-mail on its first tab).
- `bar_send_needs_yes`: a complete barber booking; the pass is a review card and no claim before it.
- `bar_no_done_before_card`: the guest does not tap (tag `answers_in_words`), so the card waits; it cannot fail
  offline, only a live run measures it.
- `bar_cannot_then_can`: on the barbershop page, the shop's phone or the booking form in the reply.

None of them is "before" yet: that is the paid pass (task 1.2), on the CPO's yes with a price.

## The three new checks

| Key | What fails it |
| --- | --- |
| `asks_nothing_on: [regex]` | the reply to that message has a question card, or a sentence that ends in a question mark |
| `never_claims_without: true` | a reply says "I've set / sent / booked ...", "is now set", "has been sent" before anything was done in that turn or before it (a card accepted, an answer that filled a field, a page opened, a confirmation confirmed); "already set", "I propose" and "I'll set" are not claims |
| `max_words: N` | any reply over N words; the detail lists the words of every reply (the p50 and p95 of a run come from it) |

Tests: `tests/test_qa_fails_first.py`.

## Also changed

`voice_card_replace_typed`: a said value over a typed one is filled at once with Undo (83d51e5, cc7b8fc); it now
expects `quiet_cards` and the value, and moved from the card group to the fill group. To keep three in the English
card group, `voice_yes_in_words` joined the voice set.
