## Mini-brief (ui-craft)

1. **Who and why.** A developer reading the docs asks how to do something and wants code they can paste, or where something is documented.
2. **Main action.** Copy the code (the code card's Copy), or open the page (a page card). One filled action per card at most.
3. **Tap ladder.** Before: read a long answer, find the code, select it, copy (4+ steps), type the next question. After: Copy on the card (1), tap a follow-up chip (1).
4. **States.** Searching (the "Searching the docs" step), answer streaming, cards after the text, nothing found (one sentence and the closest page card), limit reached (a sentence with the quick start link), error (the widget's human error line with Try again).
5. **Phone.** Cards are full width; code scrolls inside its card; chips wrap; tabs scroll sideways.

## Decisions

- **Verbatim code.** Every fenced block in the corpus gets an id (`b12`) and a marker line in the passage text. `show_code` takes ids; the server copies the blocks, so a key the docs do not have cannot appear in a code card.
- **Cards after text.** Cards and follow-ups are collected during the tool rounds and sent after the final text, like Herefront's chat: text first, then the thing to tap, follow-ups last.
- **Own plugin, same widget.** The widget's shell (typing, composer, themes) stays; the form plugin is not loaded. The docs cards are site code (`site/src/ask/`), styled through a widget theme's `css`.
- **Limits.** In memory, one process: per thread id, per address (minute and day), per site per day.
