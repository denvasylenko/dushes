# Design

## Mini-brief (ui-craft)
1. **Who and why:** a developer embeds `<agui-chat>` and wants it in their brand, in light and dark.
2. **Main action:** one call, `defineTheme("acme", {...})`, then `theme="acme"`.
3. **Tap ladder:** today a dark-aware brand needs hand-written CSS for `agui-chat.dark` and breaks when tokens are set inline. After: one object with `tokens`, `light`, `dark`.
4. **States:** unknown theme name -> the default theme and one console warning; a theme registered after the element renders -> applied when registered; unknown token keys -> a warning, ignored.
5. **Phone:** nothing changes in layout; themes only set tokens and scoped CSS.

## Layers (lowest first)
1. The widget's base CSS: `:host { …default tokens }`, `:host(.dark) { … }`.
2. The theme: a second `<style>` in the shadow root, `:host { tokens + light }` and `:host(.dark) { tokens + dark }`, then the theme's `css`. Same specificity as the base, later in order, so it wins.
3. The page: CSS on `agui-chat` (and `agui-chat[data-scheme=dark]`) and `::part()`. Outer styles win over `:host`, so the page always has the last word.

## Theme shape
```ts
interface Theme {
  extends?: string                       // a registered theme; default: "default"
  tokens?: Record<string, string>        // both schemes
  light?: Record<string, string>
  dark?: Record<string, string>
  css?: string                           // scoped to the shadow root: .chip, .card, .msg.me …
}
```
`extends` is resolved at apply time (cycles stop at the first repeat). Keys are normalised: `accent`, `--accent` and `--agui-accent` mean `--agui-accent`. Values are written as given; a value containing `;`, `{` or `}` is dropped with a warning, so a theme cannot break out of its rule.

## Registry
A module-level `Map`. `defineTheme` dispatches `agui:themes` on `window`; every element using that name re-applies. `themes()` lists names.

## Scheme
`scheme` option and attribute. `theme` values `auto | light | dark` are read as the scheme when `scheme` is not set. With `auto`, the element listens to the media query while connected.
