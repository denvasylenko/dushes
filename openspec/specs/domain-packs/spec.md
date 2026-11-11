# domain-packs Specification

## Purpose
Keep the agent core free of any domain: everything a specific form needs (persona, filling order, field notes, rules, PII list) arrives from outside as a domain pack resolved by form id.

## Requirements

### Requirement: Resolution order
A domain pack SHALL be resolved by `form_id` in this order: a pack shipped with the form at registration, a configured provider callable, packs given in code, a JSON file `<dir>/<form_id>.json`, and finally a neutral default so that an unknown form still works.

#### Scenario: Unknown form
- **WHEN** a form `dentist_visit` has no pack anywhere
- **THEN** the agent uses the default persona and the title "Dentist visit"

#### Scenario: Pack shipped with the form
- **WHEN** a form is registered with an inline `domain` pack and a file pack also exists
- **THEN** the inline pack is used

### Requirement: Compiled documents are merged in
Knowledge compiled from the form's business documents SHALL be merged on top of the resolved pack: field notes appended to the glossary, rules and flow hints appended, and the list of documents exposed.

#### Scenario: Pack plus documents
- **WHEN** an inline pack exists and documents were compiled for the form
- **THEN** the pack source is `inline+kb` and the compiled rules appear in the system prompt

### Requirement: Packs are validated against the form
Registering a form with a pack SHALL return warnings for glossary or PII keys that do not exist in the layout.

#### Scenario: Typo in a field name
- **WHEN** the pack's glossary mentions `no_such_field`
- **THEN** registration returns "domain pack references unknown field: no_such_field"
