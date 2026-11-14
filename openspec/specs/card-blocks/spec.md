# card-blocks Specification

## Purpose
Cards of the host's own, composed from small blocks that look like the chat's own cards: laid out by the developer in a card spec on the server, filled by the model through a generated tool, drawn by the widget, answered back to the model.

## Requirements

### Requirement: Cards from blocks
The widget SHALL render a card of type `blocks` from its `blocks` list, in order. Known blocks are `title`, `text`, `note`, `row`, `image`, `place`, `stat`, `diff`, `steps`, `progress`, `swatches`, `choice`, `field`, `hours`, `preview`, `chart`, `buttons`, `links` and `divider`; consecutive `row` blocks SHALL form one grouped list. An unknown block SHALL be skipped. Colours SHALL come from the theme and a block's `tone` only.

#### Scenario: A venue card
- **WHEN** a card has a `place` block and a `buttons` block with "Yes, mine" and "No"
- **THEN** the card shows the photo, name and address, and the two buttons, the first one filled

### Requirement: Blocks load on demand in the one-script build
The one-script build SHALL leave the blocks out of `agui-chat.iife.js` and load `agui-chat.blocks.js` from its folder at the first run or the first card from blocks. A card shown earlier SHALL keep its room and be filled in place (a failed load leaves Try again); `blocksCard` SHALL return its element at once and `loadBlocks()` SHALL resolve when the blocks are here.

#### Scenario: The first card before the file
- **WHEN** a card from blocks arrives before `agui-chat.blocks.js` has loaded
- **THEN** the card is shown empty with its room kept, and its blocks appear in it when the file arrives

### Requirement: Answering a blocks card
A button with an `id` SHALL resolve the card with `{action, label, values}`, where `values` holds the card's `choice`, `swatches` and `field` values by name, and SHALL fold the card into a result line with the button's label. A `links` entry SHALL open its link, call, route, share sheet or copy its text without resolving the card; a `calendar` entry SHALL open its choices in place: Apple Calendar (an .ics file), Google Calendar and Outlook, in local time.

#### Scenario: Picking a palette
- **WHEN** the user taps a swatch named `palette` and then "Use it"
- **THEN** the card resolves with `{action: "use", label: "Use it", values: {palette: "<swatch id>"}}`

### Requirement: Choices with captions, unavailable options, more and dependencies
A `choice` SHALL take a `label` (a caption above its chips), options with `off` (shown, not choosable), `more: {label, options}` (a chip that shows the rest in place), `value` (chosen at the start) and `depends: {on, options: {<id>: [...]}}` (its options follow another choice and the pick is cleared when that changes).

#### Scenario: Other days
- **WHEN** the user taps a choice's "Other days" chip
- **THEN** the chip gives way to the rest of the days, in place

### Requirement: A following choice says what comes first
A choice with `depends.empty` SHALL show that text as one quiet line, as high as a row of chips, while the choice it follows has no options for it; its chips SHALL take that line's place when they arrive, so nothing below moves.

#### Scenario: Times before a day
- **WHEN** a picker's `time` group has `depends: {on: "day", empty: "Pick a day first"}` and no day is chosen
- **THEN** the Time caption has the line "Pick a day first" under it, and tapping Friday replaces it with Friday's times

### Requirement: The main button waits for what is required
A `choice` or `field` with `required`, and an `hours` block, SHALL keep the card's primary button disabled, with a line under it naming what is missing (`need` on the `buttons` block, "Choose: {x}" by default); the line keeps its place so the button never moves.

#### Scenario: Times follow the day
- **WHEN** a card has `day` and `time` choices with `depends: {on: "day"}` and the user taps another day
- **THEN** the times of that day replace the others, none is chosen, and the line says "Choose: Time"

### Requirement: A picker card
A card of type `picker` (`title`, `groups`, `depends`, `fields`, `submit`, `need`) SHALL draw as blocks: a title, one required single choice per group, the fields and one primary button; it SHALL answer `{action: "submit", label, values}` (or reach `onAction` first).

#### Scenario: A table booking
- **WHEN** the user picks a day, a time and the number of people, types a phone and taps "Book"
- **THEN** the answer is `{action: "submit", values: {day, time, people, phone}}`

### Requirement: Opening hours and a site preview
An `hours` block SHALL edit `[{days: [0..6] (0 = Monday), from, to}]`: presets in one tap, weekday chips (several at once), from and to times, up to three pairs; its value comes back under its `name`. A `preview` block SHALL show a live view-only thumbnail of an https page (`ratio` `16:10` or `9:16`), drawn at the page's own width and scaled to the card, sandboxed, opening `href` on tap.

#### Scenario: Weekdays nine to six
- **WHEN** the user taps the preset "Mon–Fri 09:00–18:00" and Save
- **THEN** the values hold `hours: [{days: [0, 1, 2, 3, 4], from: "09:00", to: "18:00"}]`

### Requirement: Charts in cards
A `chart` block SHALL draw one of six forms in the theme's colours: `bar` (columns, `highlight` keeps one in colour and greys the rest), `line`, `area`, `barList`, `stacked` (each part's share in a legend) and `meter` (a value against `max`, with a `limit` mark, red over the limit). Columns, line and area SHALL load Chart.js only when such a chart shows.

#### Scenario: A rate over six months
- **WHEN** a card has `{type: "chart", kind: "line", unit: "%", labels: [Jun..Nov], series: [{name: "Rate", data: [...]}]}`
- **THEN** a line is drawn with its last point marked, the axis reads "17%", "18%", and "Show data" lists the six months

### Requirement: A chart's data and its text form
A `chart` SHALL take `data: [{label, value}]` or `labels` with `series: [{name, data}]` (at most 8 series, 60 points), format numbers in the chat's language with `unit`, show a legend for two or more series, a text summary for screen readers and the numbers in a table under "Show data", and say "No data for this period" instead of drawing empty axes.

#### Scenario: Nothing to show
- **WHEN** a chart comes with `data: []`
- **THEN** the card says "No data for this period"

### Requirement: Card specs become tools
A card spec (`type`, `description`, `data`, `blocks`, `wait`) in the config SHALL become a model tool `show_<type>` whose parameters are `data`. Calling it SHALL send the card filled from the arguments: as an interrupt that waits for the answer when `wait` is true, else as a `CUSTOM card` event while the turn goes on.

#### Scenario: Is this your barber?
- **WHEN** the model calls `show_barber_match` with a name, a photo and a rating
- **THEN** the chat shows the card filled with them and the turn waits for the answer

### Requirement: Filling a card spec
`{name}` placeholders in the blocks SHALL be filled from the tool's arguments; a placeholder that is the whole value SHALL keep lists and numbers; a block whose `if` names an empty value SHALL be dropped. A spec with an unknown block or a placeholder not in `data` SHALL be refused when the config loads.

#### Scenario: An optional photo
- **WHEN** a `place` block has `if: photo` and the model gives no photo
- **THEN** the card is shown without that block

### Requirement: A button that fills form fields
A button MAY carry `fills: {field: value}`. When the card is shown, each value SHALL be checked against its field and written in the form's own format, with the field's label and previous value in `fill_meta`; a value the field does not take SHALL be a tool error for the model. A tap SHALL apply the fills through the form, fold the card into its result line with Undo, and resume with the new config; the model SHALL be told those fields are filled and not to propose them again.

#### Scenario: Yes, book Maria
- **WHEN** the user taps "Yes, book Maria" with `fills: {barber: "maria"}`
- **THEN** the Barber field is filled at once, Undo is offered, and no field-change card follows

### Requirement: The answer goes back to the model
The resume of a blocks card SHALL be given to the model as text naming the button (label and id) and the values, or that the user skipped it.

#### Scenario: Yes
- **WHEN** the user taps "Yes, that's my barber" (id `yes`)
- **THEN** the tool result says the user chose "Yes, that's my barber" (yes)

### Requirement: The host handles a button itself
The formguide plugin's `onAction(card, {id, label, values}, chat)` SHALL be called first when a blocks card's button is tapped; when it returns true, the chat SHALL do nothing more (no message, no answer). Display cards SHALL be redrawable with `chat.updateCard(card.card_id, patch)`.

#### Scenario: Saving a step
- **WHEN** the host's onAction saves the opening hours for "Save hours" and returns true
- **THEN** no message is sent, and the host's updateCard shows the step done in the same card

### Requirement: The page learns what was filled
Every fill through the plugin (a field card, a one-tap answer, a button's `fills`, an action chip) and every Undo SHALL dispatch `agui:applied` on the chat with `{fields, values, undo}`.

#### Scenario: Scrolling a preview
- **WHEN** a button fills `barber`
- **THEN** the page gets `agui:applied` with `fields: ["barber"]`

### Requirement: Blocks only for clients that draw them
The card tools SHALL be offered only when the client lists the `blocks` capability, or sends no capability list.

#### Scenario: A client without blocks
- **WHEN** the client's capabilities do not include `blocks`
- **THEN** the model gets no `show_*` card tools
