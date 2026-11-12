# Proposal

## Why

formguide reads a form as a JSX skeleton plus a config `{props, state}` that a form backend rebuilds on every event. A plain React form (react-hook-form, Formik, `useState`) has neither: its fields live in components and its values in the form library. Today such a team has to write the bridge by hand: generate the JSX, assemble props from their schema and errors, convert option ids to option objects and back, push accepted values into the form, find fields for "show me where". That is the main obstacle to trying formguide on an existing React app.

## What Changes

- **A schema bridge, framework-free** (`@formguide/agui-chat/formguide`): `schemaForm(schema, access)` turns a small declarative schema (sections, fields, options, rules as functions of the values) into the JSX skeleton and a live config, applies accepted changes through the form library's own setter, and converts values between the form's format (option ids by default) and formguide's.
- **A react-hook-form hook** (`@formguide/agui-chat/react-hook-form`): `useFormguide(form, schema, options)` registers the layout once, and returns the `plugins` for `<AguiChat>` and a `ready` flag. Errors come from `formState.errors`; "show me" scrolls to `[data-name]` or the input's `name`, focuses it and calls `onReveal(section)` so the page can open its tab first.
- **Default tags for radio groups and multi-selects** in the backend: `RadioGroup: radio`, `MultiSelect: multiselect`, so generated skeletons need no server configuration.

## Capabilities

### New Capabilities
- `form-adapters`: the schema bridge and the react-hook-form hook.

### Modified Capabilities
- `component-values`: default tags `RadioGroup` and `MultiSelect`.

## Impact

- Widget package: `src/formguide/schema.ts`, `src/rhf.ts`, build entries, `package.json` exports (react-hook-form as an optional peer, types only).
- Backend: `form/layout.py` default component map; a test.
- Example: `examples/react-hook-form` (a small Vite app) and docs: `docs/chat-widget.md`, `docs/configuration.md`, `README.md` (another session edits it: only a short link), architecture pages.
