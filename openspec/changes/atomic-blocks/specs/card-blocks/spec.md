# Spec Delta

## MODIFIED Requirements

### Requirement: Cards from blocks
The widget SHALL render a card of type `blocks` from its `blocks` list, in order. Known blocks are `title`, `text`, `note`, `row`, `item`, `list`, `image`, `place`, `stat`, `when`, `diff`, `steps`, `checklist`, `facts`, `receipt`, `progress`, `swatches`, `choice`, `field`, `hours`, `preview`, `chart`, `rating`, `countdown`, `share`, `buttons`, `links` and `divider`; consecutive `row` or `item` blocks SHALL form one grouped list. An unknown block SHALL be skipped. Colours SHALL come from the theme and a block's `tone` only.

#### Scenario: A venue card
- **WHEN** a card has a `place` block and a `buttons` block with "Yes, mine" and "No"
- **THEN** the card shows the photo, name and address, and the two buttons, the first one filled

#### Scenario: An unknown block
- **WHEN** a card lists `{type: "carousel"}` between two known blocks
- **THEN** the two known blocks are drawn and nothing is drawn for the unknown one

## ADDED Requirements

### Requirement: An item with three slots
An `item` block SHALL be one row with the slots `start`, `main` and `end`, each a list of atoms, drawn left to right with `main` taking the free width. Shorthand keys `title`, `subtitle`, `meta`, `price`, `value` and `chevron: true` SHALL place the matching atom (title, subtitle and meta into `main`; price, value and the chevron into `end`), followed by any atoms given in the slots. An item with nothing to show SHALL be skipped.

#### Scenario: A menu line
- **WHEN** a card has `{type: "item", title: "Full breakfast", subtitle: "Cappuccino and cornetto", price: "CHF 2.50"}`
- **THEN** the row shows the name in bold, the description under it in the secondary colour and the price at the right edge, top-aligned with the name

### Requirement: A list of items
A `list` block SHALL group its `items` (each an `item` payload, without `type`) into one inset grouped list with hairlines between rows and an optional `title` above it. After `limit` rows (default 6), the rest SHALL come behind one "Show N more" row that opens them in place.

#### Scenario: Our picks
- **WHEN** a card has `{type: "list", title: "Our picks", items: [three menu lines]}`
- **THEN** one grouped list titled "Our picks" shows the three lines with a hairline between them

### Requirement: Atoms
An atom SHALL be an object `{type, ...}` or a plain string, which counts as a `title` in `main` and a `value` in `end`. Text atoms are `title`, `subtitle`, `meta`, `badge` (with `tone`), `price` and `value`. Image atoms are `icon` (a name from the widget's icon set), `avatar` (an image, or the first letter of `text`) and `image` (a square thumbnail). Only https and inline image URLs SHALL be drawn. An unknown atom SHALL be skipped.

#### Scenario: A popular service
- **WHEN** an item has `main: [{type: "title", text: "Haircut"}, {type: "badge", text: "Popular", tone: "accent"}]` and `end: ["30 €"]`
- **THEN** the row shows "Haircut" followed by a small accent badge, and "30 €" at the right

### Requirement: Controls in a row
The atoms `check`, `toggle` and `stepper` (`min`, `max`, `step`, `value`) SHALL be controls. Their value SHALL go into the card's values under their `name`, and they take part in `required` like `choice`. A `button` atom (`id`, `label`, `style`) SHALL answer like a button of the `buttons` block. A `chevron` SHALL only mark that the row leads somewhere. Each control's tap target SHALL be at least 44 px high on touch screens.

#### Scenario: Two extra shots
- **WHEN** an item has `end: [{type: "stepper", name: "shots", min: 0, max: 4, value: 0}]` and the user taps plus twice, then the card's primary button
- **THEN** the answer's values hold `shots: 2`

### Requirement: A row that leads somewhere
An item's `tap` SHALL make the whole row one button with a pressed state and a chevron at the end, unless `end` already holds a control. Its forms are:
- `{say: text}` sends the text as the user's message;
- `{link: url}` opens an https link;
- `{action: id}` answers like a button with that id, or goes to the host's `onAction`;
- `{details: [blocks]}` opens those blocks under the row, and closes them on a second tap.

A row with a `tap` SHALL NOT hold a `button` atom.

#### Scenario: A service opens its times
- **WHEN** a display card has an item `{title: "Haircut", tap: {say: "Book a haircut"}}` and the user taps the row
- **THEN** "Book a haircut" is sent as the user's message

### Requirement: Existing rows share the item's look
The `row`, `place` and `steps` blocks SHALL keep their payloads and SHALL be drawn with the same row layout as `item`. A card that rendered before this change SHALL render with the same content and order.

#### Scenario: An old card
- **WHEN** a card made of `title`, two `row` blocks and `buttons` is shown
- **THEN** it shows the same labels, values and buttons as before, the rows as one grouped list

### Requirement: Date and time at a glance
A `when` block SHALL show `date` (an ISO date, formatted in the chat's language as weekday, day and month) on one line, and `time` large under it. It SHALL take an optional `label` above both and an optional `end` time, shown as "13:30–14:30". A date that does not parse SHALL be shown as given.

#### Scenario: Request sent
- **WHEN** a card has `{type: "when", label: "Request sent", date: "2026-11-16", time: "13:30"}` in English
- **THEN** it reads "Request sent", "Monday, November 16" and a large "13:30"

### Requirement: Opening hours to read
An `hours` block with `mode: "read"` SHALL list `value` (the same `[{days, from, to}]` shape) by weekday, joining runs of days with the same hours ("Mon–Fri 09:00–18:00") and listing closed days as "Closed". It SHALL mark today's line. It SHALL show "Open now · until 18:00" or "Closed · opens Mon 09:00" in the visitor's local time, or in `timezone` when one is given. In read mode it SHALL have no value of its own.

#### Scenario: Saturday afternoon
- **WHEN** the hours are Mon–Fri 09:00–18:00 and Sat 10:00–14:00 and it is Saturday 15:00
- **THEN** the block shows "Closed · opens Mon 09:00" and marks the Saturday line

### Requirement: A link to share
A `share` block SHALL show `url` without its scheme, an optional `title` and `note`, and one primary action. The action is Share, which opens the system share sheet where the browser has one, or otherwise Copy. Copy SHALL change its label to "Copied" for two seconds. An optional `open: true` SHALL add a secondary Open. Only https URLs SHALL be shown.

#### Scenario: No share sheet
- **WHEN** the browser has no share sheet and the user taps Copy
- **THEN** the link is on the clipboard and the button reads "Copied" for two seconds

### Requirement: Facts to confirm
A `facts` block SHALL list `items: [{key, label, value, ok?}]`. Each row not yet `ok` SHALL offer Right and Edit. Right SHALL mark the row confirmed in place. Edit SHALL open a field under the row with the value, Save and Cancel. The block's value under its `name` SHALL map each key to `{value, ok}`. With `required: true`, the card's primary button SHALL wait until every row is confirmed.

#### Scenario: A phone number corrected
- **WHEN** the user taps Edit on "Phone", types a new number and Save, then Right on "Hours"
- **THEN** both rows read as confirmed and the values hold the new phone with `ok: true`

### Requirement: A checklist to tick
A `checklist` block SHALL list `items: [{id, label, done?, hint?}]` with a check at the start of each row. A tap SHALL toggle the row. Its value under its `name` SHALL be the list of ticked ids, and an optional `title` may show "{left} left". With `required: true`, the primary button SHALL wait until every row is ticked.

#### Scenario: Before publishing
- **WHEN** a checklist has three rows, one done, and the user ticks the other two
- **THEN** the title's "{left} left" reads 0 and the values hold all three ids

### Requirement: A receipt
A `receipt` block SHALL list `items: [{label, qty?, price}]` with the prices aligned at the right, then a hairline and `total` in bold. Optional `lines: [{label, value}]` (a tip, a discount) SHALL go between the items and the total. Prices SHALL be shown as given.

#### Scenario: Breakfast for two
- **WHEN** a receipt has two items, a line "Service 10%" and total "CHF 5.50"
- **THEN** the items, the service line and the bold total are aligned on one right edge

### Requirement: A rating
A `rating` block SHALL show `value` out of five as stars with the number beside it. With a `name`, it SHALL instead ask: five 44 px stars, where a tap sets the value and arrow keys move it. The chosen value goes into the card's values.

#### Scenario: Rate the visit
- **WHEN** a rating has `name: "stars"` and the user taps the fourth star
- **THEN** four stars are filled and the values hold `stars: 4`

### Requirement: A countdown
A `countdown` block SHALL show the time left until `at` (an ISO time) in the chat's language ("In 2 h 15 min", "In 5 min"), updated every minute, with an optional `label`. When `at` has passed, it SHALL show `done` (default "Now"). A time that does not parse SHALL hide the block.

#### Scenario: The appointment is near
- **WHEN** `at` is 4 minutes away
- **THEN** the block reads "In 4 min", and after 4 minutes it reads "Now"

### Requirement: The server knows the new blocks
A card spec in `formguide.yaml` or `GuideConfig.cards` SHALL accept the new blocks. It SHALL refuse at load:
- an atom whose `type` is not one of the atoms;
- a `tap` with none or more than one of `say`, `link`, `action`, `details`;
- an item with both a `tap` and a `button` atom.

#### Scenario: A misspelt atom
- **WHEN** a card spec has an item with `end: [{type: "prise"}]`
- **THEN** loading the config fails naming the card, the block and the unknown atom
