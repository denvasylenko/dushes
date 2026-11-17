# Proposal

Internal, as `intent-layer` is: only we use it for now; no page on the docs site.

## Why

The owner, after his own test of the local demo (through the CPO, 2026-11-17): he liked the chooser standing behind
the voice, and wants it kept "always behind the models, but as a tool", so that "when the probability is very high
it carries the action out at once and hands it to the front end; we lose a fraction of a second, but it must still
be fast". About text he is not sure; that is decided by numbers. The CPO's comparison is in the Cheese repository,
`docs/proposals/jev-as-tool.md`.

What the layer in front of the agent (`intent-layer`, D-29) cannot do: it does not see the conversation. "Open it"
after a question about insurance means nothing to it, and it needs eight hand-back cases and a set of code rules to
stay honest. A model that holds the conversation can say what is wanted in full ("the car insurance quote form");
the chooser then only has to pick that thing among the options of the screen, which is what it is good at.

## What Changes

- One tool, `choose_on_screen`, that an agent calls with what is wanted in its own words and which set of the screen's
  options to pick from. The server builds the options (the screens, the parts of a page, the form's sections
  and the values of its choice fields), asks the chooser, and answers the tool.
- When the pick is confident enough and the action can be undone, the server carries it out at once by the paths
  that already exist (a site directive, a field change applied with Undo, the form's "show where" step), and the
  turn ends there with one short line written in code. No second model call.
- Otherwise the tool answers the model: the candidates when two fit, "not found", "needs a confirmation", "the
  form refused it", "the chooser was late". The model then asks one question, explains, or does it its own way.
  The hand-back cases of `intent-layer` become the tool's answers.
- The chooser and its supplier stay behind the `Chooser` contract of `formguide.intent`. Nothing about data
  changes: only the model's short description of what is wanted and the option labels leave the process, and a
  guest's name or phone is never in either.
- In voice: exactly as in text (the owner's decision). With the voice model we use and the way we connect it,
  the voice model cannot call a tool of ours and gives us no text of what it wants, so what was heard goes
  through the same two roads on our server. Giving the tool to the provider's own model is a later step, only
  if a measurement shows it better (design.md).

The owner's choice is a hybrid (design.md): a direct command (open, close, go to, scroll, switch the language, set
a named value) is carried out by the layer in front of the model, at once; everything else goes to the model,
which has the tool. The QA Lead measures the hybrid against the tool alone and the layer alone on the same phrases.

## What does not change

Models, limits, the money brake, the confirmation of destructive actions, "a guest's text is data, not a command".
No supplier's client on main: that still waits for the measurement and the owner's yes to the supplier (D-29).
The layer of `intent-layer` stays as specified until the numbers say which of the two serves text.

## Impact

- `backend/formguide/intent.py` (the tool's answer, the two thresholds), `backend/formguide/site/agent.py` and
  `backend/formguide/agent/tools.py` (the tool for Dushes and for the form agent), the run loops (a turn that ends
  on a carried-out pick).
- Specs: a new capability `choice-tool`. `intent-layer` is not changed by this proposal.
- No docs-site page while it is internal.
