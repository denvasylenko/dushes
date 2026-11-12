## ADDED Requirements

### Requirement: Themes
A theme SHALL be an object with optional `extends`, `tokens` (for both schemes), `light`, `dark` and `css` (scoped to the widget). `defineTheme(name, theme)` SHALL register it, and the `theme` option or attribute SHALL apply a registered name or an object. The widget SHALL ship `default` and `contrast`. An unknown name SHALL fall back to `default` with one console warning.

#### Scenario: A brand theme
- **WHEN** a page calls `defineTheme("acme", {tokens: {accent: "#0a7f6f"}, dark: {accent: "#4fd1c1"}})` and sets `theme="acme"`
- **THEN** buttons use #0a7f6f in the light scheme and #4fd1c1 in the dark one

#### Scenario: Registered later
- **WHEN** the element has `theme="acme"` before `acme` is defined
- **THEN** it uses the default theme, and switches to `acme` as soon as it is defined

### Requirement: Theme layering
Theme values SHALL override the widget's defaults, and CSS on the element from the page SHALL override the theme. Theme token keys MAY omit the `--agui-` prefix. A value containing `;`, `{` or `}`, and an unknown key, SHALL be ignored with a warning.

#### Scenario: Short keys
- **WHEN** a theme has `tokens: {radius: "4px"}`
- **THEN** `--agui-radius` is 4px inside the widget

### Requirement: Scheme
The `scheme` option and attribute SHALL take `auto`, `light` or `dark`. `auto` SHALL follow the system setting, including changes while the page is open. For compatibility, `theme` set to `auto`, `light` or `dark` SHALL act as the scheme. The element SHALL reflect `data-scheme` (`light` or `dark`) and `data-theme` (the theme name, or `custom` for an object), and keep the `dark` class.

#### Scenario: The system turns dark
- **WHEN** the scheme is `auto` and the system switches to dark mode
- **THEN** the widget turns dark without a reload and `data-scheme` becomes `dark`

#### Scenario: Page CSS per scheme
- **WHEN** the page has `agui-chat[data-scheme="dark"] { --agui-accent: #4fd1c1 }`
- **THEN** that accent applies only in the dark scheme

### Requirement: Complete tokens
Every colour, shadow and radius in the widget's CSS SHALL come from a token. Besides the existing ones, the widget SHALL define `--agui-radius-sm`, `--agui-radius-lg`, `--agui-radius-pill`, `--agui-shadow`, `--agui-scrim`, `--agui-on-ok` and `--agui-on-danger`.

#### Scenario: Square corners
- **WHEN** a theme sets `radius`, `radius-sm`, `radius-lg` and `radius-pill` to `0`
- **THEN** cards, buttons, chips, the composer and the floating button have square corners
