# Proposal (status: idea, not scheduled)

## Why

The form's skeleton is JSX-like markup. A React app has it; a Vue, Angular or server-rendered app has to write it by hand, which keeps those frameworks out. The page already marks fields with `data-name` for highlights, so the skeleton could be read from the live DOM instead. The owner decided to wait; this records the idea.

## What Changes (when scheduled)

- A browser helper (in the formguide plugin) that walks the DOM by `data-name` (and roles such as tabs, accordions and sections) and builds the same skeleton the server registers today, for any framework.
- It runs when the form is ready and again when the structure changes (a debounced observer), and registers a new layout only when the skeleton's hash changes.
- Labels, options and required come from the DOM (labels, `<option>`, `required`, `aria-*`), values from the existing `getState`.

## Capabilities

- `form-adapters`: a DOM adapter beside the React and react-hook-form ones.
