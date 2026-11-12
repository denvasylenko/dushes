# Proposal

## Why

A host restyles `<agui-chat>` today with `--agui-*` tokens on the element and `::part()`. That works for one scheme only:
- a token set on the element (CSS or `style.setProperty`, as the HTML example does) beats the widget's own dark tokens, so a branded light accent stays on a dark panel;
- there is no way to give light and dark values, or to package a look under a name and reuse it across pages;
- some colours, shadows and radii are hard-coded, so a theme cannot change them (square corners, a coloured scrim, white text on the success mark);
- `scheme: auto` reads the system setting once and does not follow it when it changes.

## What Changes

- **Themes.** A theme is `{tokens, light, dark, css}`: tokens for both schemes, per-scheme overrides, and optional CSS scoped to the widget's shadow root. `defineTheme(name, theme)` registers one; `theme: "acme"` (attribute or option) or `theme: {…}` (an object) applies it. Themes may `extends` another.
- **Built-in themes:** `default` (today's look) and `contrast` (high contrast, stronger lines and focus).
- **Scheme separate from theme:** `scheme: auto | light | dark`. `theme: "auto" | "light" | "dark"` keeps working as the scheme, for compatibility.
- **Live auto scheme:** follows `prefers-color-scheme` changes.
- **Host state for page CSS:** the element reflects `data-scheme` and `data-theme`, so page CSS can write `agui-chat[data-scheme="dark"] { --agui-accent: … }`.
- **More tokens:** `--agui-radius-sm`, `--agui-radius-lg`, `--agui-radius-pill`, `--agui-shadow`, `--agui-scrim`, `--agui-on-ok`, `--agui-on-danger`; no hard-coded colours left in the widget's CSS.
- **Short keys:** theme tokens may be written without the prefix (`accent` = `--agui-accent`); unknown keys warn once.

## Capabilities

### Modified Capabilities
- `chat-widget`: themes, scheme, host attributes, the token list.

## Impact

- Widget: `src/styles.ts`, `src/themes.ts` (new), `src/element.ts`, `src/types.ts`, `src/index.ts`, `src/react.ts` (prop passthrough), tests.
- Examples: `examples/widget-html` (a theme picker; tokens through a theme instead of inline styles).
- Docs: `docs/chat-widget.md` (the Look section), `docs/architecture-pages.html` widget page if it lists tokens.
- Not breaking: existing tokens, parts, `theme="dark"` and the `.dark` host class keep working.
