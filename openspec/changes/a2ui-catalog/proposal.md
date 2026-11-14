# Proposal (status: idea, not scheduled)

## Why

A2UI (https://a2ui.org/, Apache 2.0, v1.0) is an open format for declarative JSON UI from a catalog the client registers, with AG-UI listed as a transport and renderers for React, Lit, Angular, Flutter, SwiftUI and Compose. Our cards from blocks (19 blocks today, `formguide/cards.py`, `packages/agui-chat/src/formguide/blocks*.ts`) solve the same problem in our own format. If our blocks can be an A2UI catalog, hosts get renderers on every platform and the agent speaks a standard instead of ours. The owner decided to wait; this records the spike so `atomic-blocks` is decided after it.

## What Changes (the spike, when scheduled)

- Map the 19 blocks to an A2UI catalog (names, props, data binding) and list what does not map.
- Render two cards (opening hours, a chart) in `<agui-chat>` from A2UI messages over AG-UI.
- Measure the one-script bundle against its budget (54 KB gzip) with an A2UI renderer in it.
- Decide: pass means `atomic-blocks` becomes "our components as an A2UI catalog"; fail means `atomic-blocks` goes on in our own format.

`atomic-blocks` does not start before this decision.

## Capabilities

- `card-blocks`: possibly an A2UI catalog of the blocks (only after the spike).
