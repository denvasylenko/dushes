# Proposal

## Why

When the agent changes a field, the chat rings it and blinks it green; "look here" rings a field and shows a hint. Both live inside the widget's formguide plugin. The owner wants developers to get the same effect on their own components, with or without the chat, and to style it.

## What Changes

- **Base, framework-free**: `highlightField(target, opts?)` from the subpath `@formguide/agui-chat/highlight` (the one-script build: `AguiChat.highlightField`). `target` is a field name (looked up as `[data-name]`, then `[name]`; an input inside a `[data-name]` box rings the box) or an element. `opts`: `kind: 'changed' | 'look'` (default `changed`), `hint`, `style: 'ring' | 'glow' | 'pulse'`, `root`, `scroll`. `look` scrolls, focuses (not on touch) and shows the hint bubble: today's "look here" moves onto this base. Calling it again restarts the effect; it returns a cancel function.
- **Markup and CSS**: for the length of the effect the field carries `data-agui-highlight="changed|look"` and `data-agui-highlight-style="ring|glow|pulse"`. Variables: `--agui-highlight-color` (green for changed, the system Highlight for look), `--agui-highlight-width` (2px), `--agui-highlight-radius` (the field's own), `--agui-highlight-ms` (1200), `--agui-highlight-count` (2 blinks). Reduced motion: a steady ring, no blink. The base adds its small stylesheet itself (to the document, or to the shadow root holding the target).
- **Trigger**: no new event. The formguide plugin highlights every name it applies (plugin option `highlight`, default true; false when the host draws its own). `agui:applied` is unchanged.
- **Wrappers, thin**: React `<HighlightTarget name>` (a real box with `data-name`, `as` for span or label) and `useHighlight()`; web component `<agui-highlight name>`.
- **Versioning**: public API under the widget's semver: the functions, the two attributes, the five variables and the wrapper names. Timings and the shade of green are not.

## Capabilities

- `chat-widget-formguide`: the field highlight.

## Impact

`packages/agui-chat` (built by the widget designer after the live landing demo; inside the bundle budget), a showcase page and a card-gallery specimen (Docs Lead), the frontend reference.
