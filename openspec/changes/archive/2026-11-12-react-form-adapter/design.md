# Design

## Mini-brief (ui-craft)
1. **Who and why:** a developer with an existing react-hook-form form wants the assistant next to it.
2. **Main action:** describe the form once, call one hook, render `<AguiChat plugins={plugins} />`.
3. **Ladder:** today: JSX by hand + config assembly + value conversion + directive handling (about 150 lines). After: a schema and three lines.
4. **States:** layout registration fails -> `error` from the hook, the chat stays hidden (`ready` false); a field the schema does not know is ignored on apply with a console warning.
5. **Phone:** nothing new on screen; "show me" scrolls the field into the middle and focuses it without opening the keyboard on touch screens.

## Schema
```ts
interface FieldSchema {
  name: string; label?: string
  type?: 'text' | 'textarea' | 'number' | 'date' | 'select' | 'radio' | 'multiselect' | 'bool'
  options?: Option[] | ((values) => Option[])        // Option = string | {id, name} | {value, label}
  visible?: boolean | ((values) => boolean)
  disabled?: boolean | ((values) => boolean)
  required?: boolean | ((values) => boolean)
  readonly?: boolean; placeholder?: string; help?: string
  valueAs?: 'id' | 'option' | 'name'                  // how the form stores a choice; default 'id'
}
interface FormSchema { id: string; title?: string; sections: { name: string; label?: string; fields: FieldSchema[] }[]; domain?: object; layout?: 'tabs' | 'sections' }
```
- JSX: `<Form name=id><Tabs name="tabs"><Tab name=section>…</Tab></Tabs></Form>` (or `<Section>` per section without tabs). Tags: Input, TextArea, NumberInput, DatePicker, Dropdown, RadioGroup, MultiSelect, Checkbox.
- Config: `props[name] = {label, visible, disabled, required, readonly, placeholder, options, error}`; `props[section] = {label}`; `state[name]` = the value, choices converted to option objects (`{id, name}`).
- Apply: formguide sends option objects (the default stored shape). The bridge converts to `valueAs` and calls `setValue`; returns the rebuilt config.
- Disabled containers: a section is disabled when all its fields are disabled (the agent then explains the lock).

## Hook
- `useFormguide(form, schema, {url = '/agent/run', baseUrl, getUi, onReveal})`.
- Registers the layout with `POST {base}/layouts {jsx, form_id, domain, config}` once per schema; keeps `jsx_hash`; warnings go to the console.
- `getState` uses `form.getValues()` and `form.formState.errors`; `ui.focused` from `document.activeElement`'s name.
- `applyChanges` calls `form.setValue(name, v, {shouldDirty: true, shouldValidate: true})`.
- No runtime import of react-hook-form: the hook takes the form object structurally.
