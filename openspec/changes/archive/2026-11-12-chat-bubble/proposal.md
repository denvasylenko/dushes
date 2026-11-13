# Proposal

## Why

The floating chat is a side drawer: a full-height panel slides in from the right and dims the page. For a helper next to a form that feels heavy; people expect a chat bubble (iMessage, Intercom): a round launcher in the corner that grows into a compact chat window and back, with a lively spring. Hosts also want to call any card from their own code (to show a question, a date picker or a review without the agent) and to replace the launcher.

## What Changes

- **`mode: "bubble"`**: a round launcher (60 px) in a corner; tapping it grows the chat window out of the launcher (spring scale and radius morph from the launcher's corner, the header, log and composer fading up one after another); the launcher's icon turns into a close mark. The page is not dimmed on a computer; on a phone the window becomes a sheet from the bottom with a grabber and a dimmed page.
- **Bubble options**: `bubbleSide` (`right` / `left`), `greeting` (a small speech bubble next to the launcher after `greetingDelay` seconds, once per visitor until closed), `motion` (`spring`, `gentle`, `none`); tokens `--agui-bubble-width`, `--agui-bubble-height`, `--agui-bubble-offset`, `--agui-launcher-size`.
- **Unread mark**: an answer that arrives while the bubble is closed puts a dot on the launcher and gives it a short bounce.
- **`render.launcher`** slot: the host's own launcher (the widget wires the click).
- **`chat.showCard(payload)`**: shows any card (field changes, questions with every variant, uploads, confirmations, reviews) without the agent and returns a promise of the user's answer.

## Capabilities

### Modified Capabilities
- `chat-widget`: the bubble mode, its options, the launcher slot, showCard.

## Impact

- Widget: `element.ts`, `styles.ts`, `types.ts`, `parts.ts`, i18n (greeting close label), tests.
- Docs: `site/` widget page (modes), themes page (tokens, launcher slot), a "Calling components" section on the cards page, the reference; the HTML example gets the bubble mode in its mode picker.
