# Design

Source: the CTO's D-29 and D-28 (the Cheese repository, `docs/decisions.md`, read 2026-11-17, not edited), and the
CPO's message of 2026-11-17 with the owner's yes to groups 1 to 4.

## Where it sits

```
phrase (typed, or heard in voice)
   |
   v
choice layer: generate the questions for this screen and form -> ask the chooser -> {id | none, confidence}
   |  confident, in time, and the kind may act by itself          |  none, unsure, late, failed, off
   v                                                               v
the action, by the existing path                                   the agent's turn, as today
(a site directive, a field change with Undo)
```

The layer never produces a new kind of effect. A navigation is the site directive the site agent already sends; a
value is the field change the form agent already proposes, marked to apply at once with Undo (`quiet`); a yes or
no to a waiting card is the card's own answer. So the widget, the Swift package and the hosts need nothing new.

## The contract

```python
@dataclass(frozen=True)
class Option:
    id: str
    label: str            # what the person would say; never a guest's name or phone

@dataclass(frozen=True)
class Question:
    kind: str             # "choice" | "noul" (a yes / no question; the answer is the probability of yes)
    about: str            # what is being decided: "turn", "screen", "element", "field:<name>", "confirm", ...
    text: str             # the question in plain words, for a chooser that reads one
    options: tuple[Option, ...] = ()     # 255 at most; empty for "noul"

@dataclass(frozen=True)
class Pick:
    id: str | None        # the option, "yes" / "no" for a noul, or None
    confidence: float     # 0..1
    ms: int
    by: str               # which implementation answered: "rules", "embed", "external", never a supplier's name

class Chooser(Protocol):
    async def choose(self, phrase: str, language: str, question: Question, screen: str) -> Pick: ...
```

`by` names the kind of implementation, not the supplier: a host's code and its logs never hold a supplier's name.

## Implementations, in order

| Name | What | Cost | In this change |
| --- | --- | --- | --- |
| `rules` | an option whose label is in the phrase word for word, yes / no words | none | yes, for tests only |
| `embed` | nearest option by embedding | none per call; a new dependency | no, and not planned: see the measurement |
| `external` | a chooser service behind the same contract | per call | no: after the measurement and the owner's yes to the supplier |
| the agent | Haiku, as today | per turn | it is the fallback, not a `Chooser` |

A setting picks one: `jev | haiku | rules | off`. `jev` and `haiku` are names of settings values only; the code
that talks to a supplier is one module behind `Chooser`, swapped with one line. Until that module exists, `jev`
and `haiku` give no chooser and the layer behaves as `off`. `rules` is for tests only and refuses to start
outside them.

## The questions are generated, not written

From the form (its layout and options, which the package already has) and the screen map (the site map, with a
host's screens and elements):

| Source | Question |
| --- | --- |
| a dropdown or radio field | `choice` over its options (label and id) |
| a date field | `choice`: today, tomorrow, the day after, a weekday; anything else is none |
| a time field with slots | `choice` over the slots |
| a number field with a small range (guests 1 to 20) | `choice` over the range |
| weekdays | `choice` |
| a checkbox | `noul`: on or off |
| the screens of the site map | `choice` |
| the elements of the current screen | `choice`, 255 at most |
| a request or a booking | `choice` by number or time; never by a name |

## Groups 1 to 4 (the first step)

1. Understanding: is it a command or plain speech (`noul`); the kind of turn (`choice`: navigate, open, pick a
   value, edit, a question, free text); an answer to a confirmation (`choice`: yes, no, not an answer); the
   language (`choice` of six).
2. Navigation: the screen; the element on it; a request or booking by number or time.
3. Values: a date, a time slot, guests, weekdays, dropdowns, radios, checkboxes.
4. Routing: is the agent needed at all; which field the free text is for.

The order per phrase: the kind of turn first. "A question" and "free text" go straight to the agent. For the
others the layer asks the one question that kind needs (which screen, which element, which value). Two questions
at most per phrase, so the deadline holds.

## Settings (internal)

Not in `formguide.config.KEYS`, so no reference page is required for them and none is written; passed in code by
our own hosts.

| Setting | Default | Meaning |
| --- | --- | --- |
| `provider` | `off` | `jev`, `haiku`, `rules` or `off` |
| `threshold` | 0.9 | below it the pick is none and the agent takes the turn; set from the QA Lead's measurement |
| `timeout_ms` | 300 | the layer's deadline for the whole phrase; late is none |
| `acts` | `navigate`, `show`, `set_field` | the kinds the layer may carry out by itself |
| `never_send` | guests' names and phones | labels and phrase parts that never leave the process; a host adds to it |

`off` is the default: a host that sets nothing behaves exactly as today.

## Actions

By itself the layer only looks (navigate, show, scroll, highlight) and makes reversible edits (`set_field`, with
Undo). Anything that submits, sends, pays, cancels or deletes is not in `acts` and cannot be put there: it goes to
the agent, which asks for the confirmation D-28 requires. Three actions are confirmed by a tap and never by a
spoken yes (deleting a site, changing the personal link and signing devices out, showing or exporting guests'
data as a list); the layer does not handle the confirmation of those at all.

## Data

- To any chooser outside the process go the phrase and the option labels, nothing else: no history, no form
  values, no page text.
- Options never hold a guest's name or phone; a request or booking is an option by its number or time.
- Guest-facing surfaces are not connected to an external chooser.
- Real phrases go to an external supplier only under a data processing agreement; until then it is measured on
  synthetic phrases.
- Every call to a paid chooser is counted in the run's stats with its time and cost, as a model call is.

## The bar, and who measures it

The QA Lead (D-23): confident wrong picks at most 1%, at least 60% of choice turns covered, p95 at most 300 ms
from `fra`. If rules and embeddings pass it, no external supplier is needed.

## The first measurement (the QA Lead, 2026-11-17, synthetic phrases)

Nobody passes the bar yet: the external chooser 1.2% confidently wrong, 43% covered, 281 ms; Haiku 0% wrong but
11% covered on new phrasings, 1.1 s; rules 13% confidently wrong on new phrasings; embeddings 10% wrong. So (the
CPO): the frame is built with the provider off; rules are never a product's provider; embeddings are not worth
the dependency; the threshold comes from the next measurement, after the questions are adjusted ("a booking for
N" against "N guests").

## What is built (the frame)

`backend/formguide/intent.py`: the contract, the generated questions for groups 1 to 4, the settings, and
`Layer.pick`, which returns a pick only when the layer is on, the kind may act by itself, nothing private is in
the phrase, the chooser answered within the deadline with an id among the options sent and a confidence at or
above the threshold. Everything else is None, which means the agent takes the turn. It is not wired into a run:
no host and no agent calls it yet, so behaviour is unchanged.

## Open, to settle before the layer is wired in

- A wrong confident pick is worse than a slow right one, so the threshold starts high and only the measurement
  lowers it.
- In voice, the layer answers before the voice's "let me check" would be said; whether that acknowledgement is
  then cancelled is decided with the first measurement.
