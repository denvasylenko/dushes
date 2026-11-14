## ADDED Requirements

### Requirement: A form's own translations
A field's props MAY carry `i18n: {<lang>: {label?, placeholder?, hint?}}` and an option MAY carry `names: {<lang>: ...}`; when a card is built for a language the form has, its labels and option names SHALL come from the form, the agent's translation SHALL be used only where the form has none, and the values sent to the form SHALL NOT change.

#### Scenario: The form speaks Russian
- **WHEN** the loan type's options carry `names: {ru: ...}` and the agent asks in Russian
- **THEN** the card shows the form's Russian names and the chosen value is the form's option id

### Requirement: The server keeps cards in the conversation's language
Before a card is sent, the server SHALL check its question, option labels, row labels, notes and shown values against the conversation's language and SHALL replace any string in another language with the form's own translation, else with a cached translation from the cheap model; values sent to the form, numbers and the user's own words SHALL NOT change, and a failed translation SHALL NOT block the card.

#### Scenario: A German conversation on an English form
- **WHEN** the user writes in German and the agent proposes the year of manufacture with an English label and note
- **THEN** the card shows the label and the note in German and the value is unchanged

### Requirement: A set language needs no model
When the host or the form sets `language`, cards SHALL use it without detecting it, their labels SHALL come from the form's translations and the widget's words from its language packs; a model translation SHALL be used only for strings the form does not translate, and never when `translate_missing` is false.

#### Scenario: A form with every Russian label
- **WHEN** a form sets `language: ru` and translates all its labels and options
- **THEN** its cards are in Russian and no model call is made to translate them
