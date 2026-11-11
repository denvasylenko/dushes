# Building the form UI: a guide for first-timers

This page explains, from zero, what your form gives the agent, what the agent sends back when it wants to fill fields, and how to build your UI components so the two fit together. No prior knowledge of formguide, LangGraph or AG-UI is needed. Every message shown here is a real one, copied from a run of the demo.

If you only have five minutes, read [The whole thing in 30 seconds](#the-whole-thing-in-30-seconds) and [The checklist](#the-checklist).

---

## The whole thing in 30 seconds

Think of the agent as **a helpful colleague sitting next to the user**. The colleague can:

- **look** at the form (it gets a copy with every message),
- **point** at a field ("it's here", which opens the right tab and highlights the field),
- **suggest** values ("shall I put *Car loan* into *Loan type*?").

The colleague **never types into the form itself**. Every suggestion is shown to the user as a card with *Accept* and *Reject* buttons. Only when the user presses *Accept* do **you** put the values in, through your normal form logic, exactly as if the user had typed them.

```
 your form  --(1) a copy of the form------------>  agent
 your form  <-(2) "point here" / "suggest this"--  agent
 user       --(3) Accept / Reject--------------->  your form
 your form  --(4) the updated form------------->  agent
```

That is the whole contract. The rest of this page is the exact shape of each message.

---

## Words used on this page

| Word | Plain meaning |
|---|---|
| **form backend** | your server that knows the form's rules (in the original setup a Java service). It decides which fields are visible, locked, required, and which options a dropdown has |
| **JSX** | the form's skeleton as text: which elements exist and how they nest. Example: `<Tab name="tab_loan"> <Input name="first_name" /> </Tab>` |
| **element** | anything in the JSX: a tab, an accordion, a field |
| **field** | an element the user fills in: text box, number, date, dropdown, checkbox, file upload |
| **container** | an element that holds others: tabs, tab, accordion, section, the form itself |
| **`name`** | the unique id of an element. Everything is matched by it |
| **props** | settings of each element right now: label, visible, disabled, required, options... |
| **state** | the current value of each field |
| **config** | props + state together: `{ "props": {...}, "state": {...} }` |
| **card** | the agent's suggestion shown in the chat with *Accept* / *Reject* |
| **directive** | the agent's "look here" instruction (open a tab, scroll to a field, highlight it) |
| **reveal** | the list of tabs and accordions to open so a field becomes visible on screen |

---

## Part 1. What you give the agent

With **every** chat message the frontend sends the current form in `state` (the AG-UI field of that name):

```json
{
  "config":   { "props": { ... }, "state": { ... } },
  "jsx_hash": "3f9a1c0d2b7e4a55",
  "form_id":  "loan_application",
  "ui":       { "activeTabs": {"main": "tab_loan"}, "openAccordions": ["acc_loan_params"], "focused": "loan_amount", "now": "2026-11-11 Wednesday 14:05" },
  "attachments": [ { "id": "att_1a2b3c4d", "filename": "passport.pdf", "bytes": 182044 } ]
}
```

| Key | Required | What it is |
|---|---|---|
| `config` | yes | props and values of the form **as your form backend last built them** |
| `jsx_hash` | yes | the id of the skeleton, returned once by `POST /agent/layouts` (see 1.1) |
| `form_id` | recommended | which form this is; picks the domain pack (persona, glossary, rules) and the document library |
| `ui` | recommended | what the user sees right now (see 1.4) |
| `attachments` | no | files the user attached to this message (from `POST /agent/attachments`) |

### 1.1 The skeleton (JSX) — sent once

When the page opens, send the JSX once:

```http
POST /agent/layouts
{ "jsx": "<Form name=\"main\">...</Form>", "form_id": "loan_application" }

-> { "jsx_hash": "3f9a1c0d2b7e4a55", "nodes": 212, "domain_pack": "dir", "warnings": [] }
```

Keep `jsx_hash` and send it with every message. The same JSX always gives the same hash, so all users of a form share one parsed copy. **Read `warnings`**: this is where the agent tells you that it does not understand something in your JSX.

**Rules for the JSX** (the parser is deliberately simple):

1. **Every element has a `name`**, and names are **unique in the whole form**. `name="x"`, `name='x'` and `name={"x"}` all work.
2. **Only the tag and `name` are read.** Every other attribute is ignored. Labels, options and flags go in props (1.2), not in the JSX.
3. **Text between tags** is read as static text the agent can quote ("Fields marked * are required").
4. **No JavaScript inside**: no `{cond && <X/>}`, no `.map()`. Conditions belong in props (`visible: false`).
5. **Tags must be known.** By default:

| Your tag | Role | | Your tag | Role |
|---|---|---|---|---|
| `Form` | form (the root) | | `Input` | text |
| `Tabs` | a set of tabs | | `TextArea` | text |
| `Tab` | one tab | | `NumberInput` | number |
| `Accordion` | a collapsible block | | `DatePicker` | date |
| `Section` | a plain group | | `Dropdown` | select |
| | | | `Checkbox` | bool |
| | | | `FileUpload` | file |

Your component library uses other names? Map them once in `formguide.yaml` (this **replaces** the default list, so list all of them):

```yaml
components:
  containers: {Form: form, TabGroup: tabs, TabPane: tab, Collapse: accordion, Fieldset: section}
  fields: {TextField: text, Money: number, Calendar: date, Select: select, Toggle: bool, Upload: file}
```

A field can also be described in more detail (how it stores its value): see 1.5. A tag that is in neither list still works but has the role `unknown`, and you get a warning `unknown tag <X> at 1.2.3`.

A tiny but complete skeleton:

```jsx
<Form name="main">
  <Tabs name="steps">
    <Tab name="tab_you">
      <Accordion name="acc_personal">
        <Input name="first_name" />
        <DatePicker name="birth_date" />
        <Dropdown name="gender" />
      </Accordion>
    </Tab>
    <Tab name="tab_loan">
      Fields marked * are required.
      <NumberInput name="loan_amount" />
      <Checkbox name="consent_pd" />
      <FileUpload name="income_proof" />
    </Tab>
  </Tabs>
</Form>
```

### 1.2 Props — the settings of each element

`config.props` has one entry per `name`. These are the keys the agent understands; any other key is passed along and ignored.

| Prop | Type | Default | What the agent does with it |
|---|---|---|---|
| `label` | string | the `name` | calls the field by this name when talking to the user and on cards |
| `visible` | bool | `true` | `false` hides the element **and everything inside it**. The agent will not suggest a value for a hidden field |
| `disabled` | bool | `false` | `true` locks the element **and everything inside it**. The agent explains why it is locked (usually: earlier required fields are empty) |
| `readonly` | bool | `false` | the value is computed by the form (e.g. `age` from `birth_date`); the agent never suggests it |
| `required` | bool | `false` | counts toward "what is left to fill"; the agent leads the user through these |
| `options` | a list of choices | — | for dropdowns, radios, multi-selects: the allowed choices **right now**. The agent picks only from this list. Another key or another shape (`items: [{value, label}]`)? See 1.5 |
| `placeholder` | string | — | shown to the agent as a format hint ("+7 ___ ___ __ __") |
| `error` | string | — | a validation message from your backend; the agent explains it and helps fix it |

Two rules worth remembering:

- **Containers pass their state down.** A field inside a hidden accordion is hidden; a field inside a locked tab is locked, whatever its own props say.
- **A field that is in the JSX but has no props entry is treated as hidden.** If a field mysteriously "does not exist" for the agent, check that your backend sends props for it.

Example (part of `config.props`):

```json
{
  "tab_loan":    { "label": "Loan", "visible": true, "disabled": true },
  "gender":      { "label": "Gender", "visible": true, "required": true,
                   "options": [ {"id": "m", "name": "Male"}, {"id": "f", "name": "Female"} ] },
  "age":         { "label": "Age", "visible": true, "readonly": true },
  "loan_amount": { "label": "Loan amount", "visible": true, "required": true, "error": "Maximum is 5,000,000" }
}
```

### 1.3 State — the values, and their exact format

`config.state` has one entry per field `name`. **The agent sends values back in the same format your form uses**, so a card's value can go to your backend as it is. With the **default** components the formats are:

| Role | Value in `state` | Example | Empty |
|---|---|---|---|
| text | string | `"Anna"` | `""` or `null` |
| number | number (a numeric string is read too) | `250000` | `null` |
| date | ISO date string `YYYY-MM-DD` | `"1990-05-31"` | `null` |
| select, radio | the option object `{id, name}` | `{"id": "f", "name": "Female"}` | `null` |
| multiselect | a list of option objects | `[{"id": "sms", "name": "SMS"}]` | `[]` |
| bool | `true` / `false` | `true` | `false` (a bool counts as filled only when `true`) |
| file | an object with at least `name` | `{"name": "salary.pdf"}` | `null` |

Your components store values differently? That is normal: describe them once (1.5).

### 1.5 Your components store values differently? Describe them

Every team builds components its own way. One dropdown stores the whole option, another only `"auto"`. One library calls the choices `options: [{id, name}]`, another `items: [{value, label}]`. A toggle may store `"Y"`/`"N"`, a date may be `"31.05.1990"`. Tell the agent **once per component tag** in `formguide.yaml`, and it will:

- **read** your form correctly: what is filled, which option is chosen, what is out of the list;
- **write** every card and prefill value in exactly your format, so you send it to your backend unchanged.

```yaml
components:
  fields:
    Input: text                                              # a bare role: default format
    Select:      {role: select, value: id, options_prop: items}   # stores "auto"; choices in props.items
    RadioGroup:  {role: radio, value: id}                    # one choice, shown as radio buttons
    MultiSelect: {role: multiselect, value: ids}             # stores ["sms", "email"]
    Toggle:      {role: bool, true: "Y", false: "N"}         # stores "Y" / "N"
    Calendar:    {role: date, format: "%d.%m.%Y"}            # stores "31.05.1990"
    Amount:      {role: number, value: string}               # stores "250000" instead of 250000
    Phone:       {role: text, codec: "my_app.codecs:PhoneCodec"}   # anything else: your own class
```

What each key means:

| Key | For roles | Values | Default |
|---|---|---|---|
| `role` | all | `text`, `number`, `date`, `select`, `radio`, `multiselect`, `bool`, `file` | required |
| `value` | select, radio | `option`: the whole option object as your props give it; `id`: only its id; `name`: only its label | `option` |
| `value` | multiselect | `options`, `ids`, `names`: a list of the same | `options` |
| `value` | number | `number` (`250000`) or `string` (`"250000"`) | `number` |
| `options_prop` | select, radio, multiselect | the props key that holds the choices | `options` |
| `option_keys` | select, radio, multiselect | `{id: <key>, name: <key>}` of an option object | detected, see below |
| `true`, `false` | bool | what the component stores when checked / unchecked | `true`, `false` |
| `format` | date | `iso`, a `strftime` pattern such as `"%d.%m.%Y"` or `"%m/%d/%Y"`, or `epoch_ms` | `iso` |
| `codec` | all | `"module:Class"`: a class with `decode(raw, props)` and/or `encode(value, props)` | none |

**Option keys are detected for you.** If your options look like any of these, you do not need `option_keys`:

| Your options | Read as |
|---|---|
| `[{"id": "m", "name": "Male"}]` | id `m`, label `Male` |
| `[{"value": "m", "label": "Male"}]` (most UI kits) | id `m`, label `Male` |
| `[{"key": ..., "label": ...}]`, `[{"value": ..., "text": ...}]`, `[{"code": ..., "name" or "title": ...}]` | the same |
| `["Morning", "Evening"]` | the text is both id and label |
| `{"m": "Male", "f": "Female"}` | id → label |

**Reading is forgiving, writing is exact.** When reading, the agent understands a choice stored as an object, an id or a label. When writing, it uses exactly the `value` you configured. With `value: option` it writes back **your own option object**, extra keys included.

**A codec** handles anything the keys cannot describe, for example a phone stored as `{country, number}`:

```python
class PhoneCodec:
    def decode(self, raw, props):      # your stored value -> what the agent reasons about (here: a string)
        return raw["country"] + raw["number"] if raw else None
    def encode(self, value, props):    # the agent's value -> what your component stores
        return {"country": value[:2], "number": value[2:]}
```

What the agent reasons about, per role: text a string, number a number, date `"YYYY-MM-DD"`, select/radio `{id, name}`, multiselect a list of `{id, name}`, bool `true`/`false`. A codec that raises never breaks the chat: a value it cannot read is shown to the agent as unreadable, and a value it cannot write is not proposed.

**Check your setup before you start.** Send the form's initial config when you register it, and the agent tells you what it cannot read, and what to set:

```http
POST /agent/layouts
{ "jsx": "...", "form_id": "loan_application", "config": { "props": {...}, "state": {...} } }

-> "warnings": [
  "loan_type <Select>: the value \"auto\" matches no option; if the component stores an id or a label, set value: id / name (multiselect: ids / names)",
  "birth_date <Calendar>: cannot read the value \"05/31/1990\" as date; set format (a strftime pattern or epoch_ms)",
  "gender <Select>: the option objects in props.options have no recognisable id/label keys (...); set option_keys"
]
```

Or offline, from the command line:

```bash
formguide check --config formguide.yaml --jsx form.jsx --form-config sample-config.json
```

It prints every tag with its resolved format, then the warnings, and exits with an error if there are any. The demo frontend sends the config on registration and prints the warnings in the browser console.

### 1.4 `ui` — what the user is looking at

| Key | Example | Why |
|---|---|---|
| `activeTabs` | `{"steps": "tab_loan"}` | for each tab set (by its `name`), the open tab |
| `openAccordions` | `["acc_personal"]` | names of the expanded accordions |
| `focused` | `"loan_amount"` | the field the cursor is in, so "what goes here?" just works |
| `now` | `"2026-11-11 Wednesday 14:05"` | the user's local time, so "next Tuesday" is understood |

All of it is optional, but with it the agent can say "the field just below" instead of a long path.

---

## Part 2. What the agent sends back

The agent streams AG-UI events. Here is **everything the frontend can receive**, and what to draw for it:

| Event | When | What to render |
|---|---|---|
| `TEXT_MESSAGE_START` / `_CONTENT` / `_END` | the agent replies | a chat bubble, filled as the text streams |
| `CUSTOM ui_directive` (2.1) | the agent points at a place in the form | open tabs and accordions, scroll, highlight, show the hint |
| `CUSTOM on_interrupt`, `type: "set_fields"` (2.2) | the agent wants to fill fields | a card with a row per field: *Fill in* / *Reject* |
| `CUSTOM on_interrupt`, `type: "ask"` (2.5) | the agent asks a question with options | a question card: option buttons and/or a text box |
| `TOOL_CALL_*` + `TOOL_CALL_RESULT` | the agent used one of its own tools | optional: a small "searching the documents..." line |
| `TOOL_CALL_*` without a result | the agent called **your** frontend tool | anything you like: it is your own component (see Integrate in the architecture pages) |
| `CUSTOM agent_note`, `agent_context`, `memory_compacted` | internal | nothing, or a debug panel |
| `RUN_FINISHED` / `RUN_ERROR` | the turn ended | stop the spinner, show the error |

**Both cards stop the turn** until the user answers; there is at most one at a time. Look at `type` to know which card to draw. The two events that change what is on screen in the form are the directive and the field-change card; both arrive as `CUSTOM` events with a JSON value.

### 2.1 "Look here": the `ui_directive` event

Sent when the agent wants to show the user a field (or a tab, or an accordion).

```json
{
  "type": "focus",
  "target": "loan_amount",
  "reveal": [
    { "type": "tab", "tabs": "main", "tab": "tab_loan" },
    { "type": "accordion", "name": "acc_loan_params" }
  ],
  "hint": "Enter the amount here"
}
```

| Key | Meaning |
|---|---|
| `type` | always `"focus"` today |
| `target` | the `name` of the element to show |
| `reveal` | steps to make it visible, **from the outside in**. `{"type": "tab", "tabs": T, "tab": X}` means: in the tab set named `T`, open tab `X`. `{"type": "accordion", "name": A}` means: expand accordion `A` |
| `hint` | a short sentence to show next to the element (may be empty) |

What your UI does, in order:

1. go through `reveal` and open each tab and accordion;
2. wait one frame (so the element is in the DOM), then scroll the element into view;
3. highlight it for a moment and show `hint`.

The directive **never changes values**; it is safe to apply at once.

```ts
function applyDirective(d) {
  for (const s of d.reveal) {
    if (s.type === "tab") setActiveTab(s.tabs, s.tab)
    else openAccordion(s.name)
  }
  setTimeout(() => {
    document.querySelector(`[data-name="${d.target}"]`)?.scrollIntoView({ behavior: "smooth", block: "center" })
    flash(d.target, d.hint)
  }, 60)
}
```

### 2.2 "Shall I fill this in?": the card (`on_interrupt`)

Sent when the agent wants to set one or more fields. The run then **stops and waits** for the user's answer. The value of the event is a JSON **string**; parse it:

```json
{
  "type": "set_fields",
  "card_id": "cc9fefa2fb8e",
  "changes": [
    {
      "name": "loan_type",
      "label": "Loan type",
      "value": { "id": "auto", "name": "Car loan" },
      "display": "Car loan",
      "reason": "You said car loan",
      "reveal": [
        { "type": "tab", "tabs": "main", "tab": "tab_loan" },
        { "type": "accordion", "name": "acc_loan_params" }
      ]
    },
    {
      "name": "first_name",
      "label": "First name",
      "value": "Anna",
      "display": "Anna",
      "reason": "",
      "reveal": [
        { "type": "tab", "tabs": "main", "tab": "tab_applicant" },
        { "type": "accordion", "name": "acc_personal" }
      ]
    }
  ]
}
```

| Key | Meaning | Use it for |
|---|---|---|
| `card_id` | id of this card | answering it; matching it after a page reload |
| `changes[].name` | which field | the key to put into your state |
| `changes[].label` | the field's label | the card's left column |
| `changes[].value` | **the value in your component's own format** (table 1.3, or what you described in 1.5), already checked: the option exists, the date is valid, the field is visible and editable | what you send to your form backend, unchanged |
| `changes[].display` | the value as text for people (`"Car loan"`, `"✓"`, `"✗"`, `"250000"`) | the card's right column |
| `changes[].reason` | why the agent suggests it (may be empty) | a small grey line under the row |
| `changes[].reveal` | how to make this field visible | after *Accept*, open the place of the last change so the user sees the result |

**Before a card is sent the agent has already checked every value.** A value for a hidden, locked or read-only field, an option that is not in `options`, or a date that does not exist never reaches a card. The agent is told the problem and has to fix it or explain it to the user. Your UI can trust `value`.

With `interrupt_mode: structured` in `formguide.yaml`, the same card arrives as `RUN_FINISHED.outcome.interrupts[0]`: `id` is the `card_id`, and `metadata.changes` is the same list. Pick whichever your client library supports. CopilotKit's `useInterrupt` uses the default (`legacy`).

### 2.3 Answering the card

**On Accept:**

1. Turn the changes into `{name: value}`: `{"loan_type": {"id": "auto", "name": "Car loan"}, "first_name": "Anna"}`.
2. Send them to **your form backend** the same way a user's typing would go (in the demo: `POST /java/event {state, changes}`). The backend applies its rules and returns the **new config**: new values, plus fields that appeared, got unlocked or got new options because of these values.
3. Show the new config in the form, and open the `reveal` of the last change.
4. Resume the agent with the answer and the **new** config:

```ts
await agent.runAgent({ forwardedProps: { command: { resume: JSON.stringify(
  { accepted: true, config: newConfig, ui: currentUi }) } } })
// AG-UI 1.0 style instead:  resume: [{ interrupt_id: card_id, status: "resolved", payload: { accepted: true, config: newConfig } }]
```

The agent then compares the old and new config, sees what your form did ("*Loan* tab unlocked, *Car brand* appeared"), tells the user, and carries on.

**Keep only some rows.** Give each row a checkbox, ticked by default. When the user unticks some and presses *Fill in*, send **only the ticked changes** to your form backend and add their names to the resume:

```ts
resume: { accepted: true, config: newConfig, names: ["first_name", "last_name"] }   // "gender" was unticked
```

The agent is told "The user applied: first_name, last_name. Declined (not applied): gender." and will not push the declined value again unless the user asks. Without `names`, *Accept* means all rows. `names: []` is the same as *Reject*.

**On Reject:** resume with `{accepted: false}` (or `status: "cancelled"`). Optionally add `comment: "wrong amount"`. Do not touch the form.

**Why not just write the values straight into the inputs?** Because your form has rules: choosing *Car loan* may show *Car brand* and change the allowed amounts. Only your form backend knows those rules. If you skip it, the agent and the screen will disagree about the form.

### 2.4 The whole round trip

```
user: "I want a car loan, my name is Anna"
  |
  |  POST /agent/run   messages:[user]  state:{config, jsx_hash, form_id, ui}
  v
agent: (thinks, looks at the form, checks values)
  |
  |  TEXT_MESSAGE_*  "Here is what I can fill in:"
  |  CUSTOM ui_directive   (optional: opens the tab, highlights a field)
  |  CUSTOM on_interrupt   {card_id, changes:[loan_type, first_name]}
  |  RUN_FINISHED
  v
your UI: shows the card  ->  user presses Accept
  |
  |  your form backend: apply {loan_type, first_name}  ->  new config
  |
  |  POST /agent/run   resume {accepted:true, config:<new>}   (same thread)
  v
agent: "Done. The Loan tab is open now; next is the amount."
```

### 2.5 "Which one?": the question card

When the user must choose between known options, or the request is ambiguous ("I want a loan": which kind?), the agent asks with a **question card** instead of listing the options in text. It is the same `on_interrupt` event with `type: "ask"`, and the turn waits for the answer:

```json
{
  "type": "ask",
  "card_id": "a41c09e2d7f3",
  "question": "What kind of loan do you need?",
  "options": [
    { "id": "consumer", "label": "Consumer loan" },
    { "id": "mortgage", "label": "Mortgage" },
    { "id": "auto", "label": "Car loan" },
    { "id": "refinance", "label": "Refinancing" }
  ],
  "multiple": false,
  "allow_text": true,
  "field": "loan_type"
}
```

| Key | Meaning | Render |
|---|---|---|
| `question` | one short question | the card's title |
| `options` | up to 12 choices, `{id, label}`; may be empty | a button per option (single choice) or a checkbox per option (multiple) |
| `multiple` | several options may be chosen | checkboxes plus a *Send* button |
| `allow_text` | a typed answer is allowed (default `true`) | a small text box: "or type your answer" |
| `field` | present when the options are a field's choices | nothing required; useful to show the card next to that field |

**Answering:**

```ts
resume: { answer: { ids: ["auto"] } }                // a clicked option
resume: { answer: { ids: ["sms", "email"] } }        // several, when multiple
resume: { answer: { text: "only on weekends" } }     // typed (a plain string works too)
resume: { accepted: false }                          // skipped (or AG-UI status: "cancelled")
// AG-UI 1.0 style:  resume: [{ interrupt_id: card_id, status: "resolved", payload: { answer: { ids: ["auto"] } } }]
```

The agent gets "The user chose: Car loan (auto)" and continues in the same turn. Usually it then sends a field-change card for `loan_type`. **The question card never changes the form by itself.** An id that was not offered, several ids for a single-choice question, or text when `allow_text` is false counts as skipped, and the agent is told why.

With `interrupt_mode: structured` the question arrives as `RUN_FINISHED.outcome.interrupts[0]` with `reason: "ask_user"`, `message` = the question, and the rest in `metadata`. A field-change card has `reason: "confirm_field_changes"` there.

---

## Part 3. How to build each component

You can use any UI library. What matters is the behaviour below.

### Every element

- **Render it by `name`**, and put the name on the outermost DOM node: `data-name="first_name"`. The agent's directives find elements by it.
- Read `label`, `visible`, `disabled`, `readonly`, `required`, `error` from `props[name]`, and **apply the container rules yourself**: do not render children of a hidden container; lock children of a locked one.
- Support a **highlight** state (a short pulse or outline) and an optional **hint** bubble, for directives.

### Fields

The agent sends values in **the same format your component stores**: the defaults below, or what you described in 1.5. So the rule is simple: *whatever your component puts into `state` on change, the agent sends the same shape.*

| Role | Shows | Stores (default) | Notes |
|---|---|---|---|
| text | `state[name]` | the string | |
| number | `state[name]` | a number | `value: string` if your input keeps strings |
| date | `state[name]` in the user's local format | `YYYY-MM-DD` | another stored format: `format:` |
| select | the chosen option's label | the option object | only the id or label: `value: id` / `name` |
| radio | one button per option | the option object | same keys as select |
| multiselect | checkboxes or chips per option | a list of option objects | `value: ids` / `names` |
| bool | checked if `true` | `true` / `false` | other stored values: `true:` / `false:` |
| file | the file name | your upload result, e.g. `{name: "salary.pdf"}` | never set by the agent: only the user uploads files. The agent points at the field instead |

- **Choices come from props** (`props[name].options`, or the key you set in `options_prop`), never from a hard-coded list. The backend may change them as the user fills the form; the agent always uses the current list.
- If the stored option is no longer in `options`, show it as invalid. The agent notices this too and tells the user.
- Show `error` under the field. The agent reads the same text.

### Containers

| Role | Must be | Why |
|---|---|---|
| tabs | **controlled**: the open tab comes from your state (`activeTabs[name]`), not hidden inside the component | a directive must be able to switch it; you report it in `ui.activeTabs` |
| tab | clickable header with `data-name`; looks locked when `disabled` | the agent says "open the *Loan* tab" and may point at it |
| accordion | **controlled** open/closed (`openAccordions`) | same as tabs |
| section, form | a plain wrapper with `data-name` | |

### The page

- On load: `POST /agent/layouts` once, keep `jsx_hash`.
- Keep one object `ui = {activeTabs, openAccordions, focused}` in your state, update it when the user clicks, and send it with every message.
- Before every run set `state = {config, jsx_hash, form_id, ui}` with the **latest** config.
- Handle the events: `ui_directive` → `applyDirective`; `on_interrupt` → look at `type`: `set_fields` → a field-change card (2.2), `ask` → a question card (2.5).
- Card buttons follow 2.3 (with a checkbox per row) and 2.5.

---

## The checklist

Copy this into your ticket.

- [ ] Every JSX element has a unique `name`; no `{...}` expressions in the JSX.
- [ ] All tags are in the default list or mapped in `components:`; `POST /agent/layouts` returns no `unknown tag` warnings.
- [ ] Every field has a props entry, with `label`; dropdowns, radios and multi-selects have their choices in props.
- [ ] Values use the default formats (table 1.3), **or** each component that differs is described in `components.fields` (1.5).
- [ ] `POST /agent/layouts` with the initial `config` (or `formguide check --jsx ... --form-config ...`) returns no warnings.
- [ ] Every element's outer DOM node has `data-name="<name>"`.
- [ ] Tabs and accordions are controlled from page state; `ui` is sent with every message.
- [ ] Every run sends the latest config in `state`.
- [ ] `ui_directive`: opens `reveal` in order, scrolls to `target`, highlights, shows `hint`.
- [ ] Card *Accept*: changes → your form backend → new config → form updated → resume `{accepted: true, config}`.
- [ ] Card *Reject*: resume `{accepted: false}`; the form is not touched.
- [ ] Card rows have checkboxes; a partial *Accept* sends only the ticked changes and `names`.
- [ ] `on_interrupt` is drawn by `type`: `set_fields` → field-change card, `ask` → question card answered with `{answer: {ids?, text?}}`, *Skip* → `{accepted: false}`.
- [ ] After a page reload, `GET /agent/threads/{id}` returns `pending_card` (`kind: "card"` or `"question"`); show it again so the user can still answer.

---

## When something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| The agent says a field does not exist | the field has no props entry, or a parent is `visible: false` | send props for every field; check the parents |
| The agent says a field is locked but it is not on screen | your UI ignores a parent's `disabled` (or the backend sends it by mistake) | apply the container rules in the UI |
| The agent offers a dropdown value that the UI cannot show | the UI uses its own hard-coded options | render `props[name].options` |
| `409` from `/agent/run` | the server does not know this `jsx_hash` | call `POST /agent/layouts` again (layouts are also kept on disk, so this is rare) |
| After *Accept* the agent describes the form wrongly | the resume sent the old config, or none | resume with the config your backend returned **after** applying the changes |
| A directive does nothing | no `data-name` on the element, or tabs/accordions are not controlled | see Part 3 |
| The agent thinks a dropdown is empty or "not in the options" although it is set | the component stores the value or options in another shape | describe the tag (1.5); register with `config` to see the warning |
| Your backend rejects a value from a card | the component expects another format (`"Y"` instead of `true`, `"31.05.1990"`, just the id) | describe the tag (1.5): the agent then writes that format |
| A question shows up as an empty "Fill in these fields?" card | the UI draws every `on_interrupt` as a field-change card | check `type`: `"ask"` is a question card (2.5) |
| The agent ignores the button the user clicked | the resume sent a label instead of the option's `id`, or a field-change answer to a question | resume with `{answer: {ids: [<option id>]}}` |
| Warnings `duplicate name x` | two elements share a `name` | make names unique; the second one is renamed `x__1.2.3` and the agent cannot set it reliably |

---

## Where to look in the code

| What | File |
|---|---|
| JSX parser and the default tag list | [`backend/formguide/form/layout.py`](../backend/formguide/form/layout.py) |
| props and state: visible, locked, filled | [`backend/formguide/form/overlay.py`](../backend/formguide/form/overlay.py) |
| value checks and the card's contents | `_norm_value`, `_t_propose_changes`, `reveal_chain` in [`backend/formguide/agent/tools.py`](../backend/formguide/agent/tools.py) |
| component value formats (1.5): reading, writing, option keys, warnings | [`backend/formguide/form/values.py`](../backend/formguide/form/values.py), `FieldSpec` in [`layout.py`](../backend/formguide/form/layout.py) |
| the demo UI: card, directives, `ui` | [`frontend/src/App.tsx`](../frontend/src/App.tsx), [`frontend/src/Form.tsx`](../frontend/src/Form.tsx), [`frontend/src/types.ts`](../frontend/src/types.ts) |
| a mock form backend that builds JSX + config | [`backend/demo/mock_forms/`](../backend/demo/mock_forms/) and `/java/*` in [`backend/demo/app.py`](../backend/demo/app.py) |
| the same with CopilotKit | [`examples/copilotkit/src/App.tsx`](../examples/copilotkit/src/App.tsx) |
| the behaviour contracts | [`openspec/specs/form-layout`](../openspec/specs/form-layout/spec.md), [`form-state`](../openspec/specs/form-state/spec.md), [`field-changes`](../openspec/specs/field-changes/spec.md), [`ui-guidance`](../openspec/specs/ui-guidance/spec.md), [`component-values`](../openspec/specs/component-values/spec.md) |
