# Design: experimental voice mode

Status: a note for the owner's decision. No code is written and nothing has been spent.
Prices and mechanics were read from OpenAI's documentation on 2026-11-15 (pricing page, the gpt-realtime-2.1 model
page, the WebRTC, server-side controls and realtime cost guides). Everything marked "estimate" is my arithmetic on
those prices, not a measurement.

## The two designs

### A. Realtime direct: the voice model is the agent

The realtime model gets the UI agent's tools (get_fields, propose_changes, ask_user, navigate, read_page,
ask_documents and the rest) and decides itself what to call; our server only executes the calls.

- For: one model, the shortest path from speech to action, the lowest delay.
- Against: it is a second agent. The instructions, the domain packs, the consent rule, the "answer first" gate,
  the "options once" rule, the card flow and the refusals live in the Dushes agent's graph and prompts and are held
  in place by QA's scenario sets (indirect-v1 alone is 56 scenarios). None of that applies to another model with
  another prompt: every rule is rewritten and every set is run again, in audio. The tool list and instructions are
  also large, and a realtime session sends the whole conversation with every response, so they are paid for on
  every turn.

### B. Hybrid: OpenAI Realtime is the voice, Dushes is the agent (recommended)

The realtime model has one tool, `ask_dushes(request)`, and one job: hear the person, pass on what they asked, say
the result in a sentence or two. The server runs the ordinary Dushes turn (the site agent or the UI agent, on
Haiku as today) with that text and returns a short result to be spoken. The turn's events (steps, text, cards,
field changes, directives) go to the widget over the AG-UI stream that exists today; the widget draws them in the
orb view as steps under the orb, small cards and short lines.

- For: one agent, one set of rules, one transcript. Every existing gate and benchmark keeps its meaning. A change
  to the agent reaches chat and voice at once. The voice model's context stays small (a short instruction, one
  tool), which is also what keeps it cheap.
- Against: one more hop. The agent's first word takes about 3 s at the median today (QA, site turns: 2.9 s, p90
  5.9 s), so the voice says a short "one moment" while the steps appear under the orb. Spoken answers are a
  summary of what the agent wrote, so the wording aloud and on screen can differ slightly; the screen is the
  record.

**Recommendation: B.** It delivers what the owner described (speak, see the steps, get small widgets and short
lines) without a second agent to keep correct. A becomes worth it only if the measured delay of B is not good
enough, and then for a narrow set of fast actions, not as a replacement.

### A third option to check before building: GPT-Live

OpenAI's pricing page also lists `gpt-live-1`, a newer voice product billed at a flat $0.05 a minute, whose
server controls speak of "delegated work" (the backend model and tools are billed separately). On paper it is
design B as a product, with a predictable price. I have read only its price and the outline of its controls; I do
not know its limits, languages or quality. Proposed first step of the work: half a day's reading and one
connection test, then choose between Realtime (gpt-realtime-2.1 or its mini) and GPT-Live as the voice. The rest
of this design does not depend on that choice.

## How it connects

```
browser (orb view)                    docs host (ours)                         OpenAI
  mic, speaker  <== WebRTC audio ==========================================>  realtime session
  SDP offer  --> POST /voice/session --> POST /v1/realtime/calls (our key) -->
             <-- SDP answer          <-- answer + call id
                                      sideband WebSocket (call id, our key) <-> same session:
                                        instructions, the one tool, usage, end of call
  AG-UI stream <-- GET /voice/events <-- the Dushes turn started by ask_dushes
```

- **No key in the browser, not even a short-lived one.** The CPO's outline has the host mint an ephemeral client
  secret. I recommend the other documented way, the "unified interface": the browser sends its connection offer to
  our host, the host creates the call with our key and returns the answer. The host then holds the call id and can
  attach its control connection. Developers report that attaching fails when the call was created with a
  different key than the one attaching; creating the call ourselves avoids that class of failure.
- **The control connection (sideband)** is where our server sets the instructions and the tool, receives
  `ask_dushes` calls and answers them, reads the usage of every response, and ends the call.
- **Interruption** is the realtime session's own: it detects speech, stops its answer and drops audio not yet
  played. On an interruption our server also stops the Dushes turn in progress (`POST /stop` exists).
- **Cards.** A card shows in the orb view as a small widget and can be tapped as today. A spoken answer to an open
  card goes to it as a typed answer; "skip" closes it. Field-change cards keep their Accept: voice never applies a
  change the person did not confirm, by tap or by an explicit yes.
- **Back to chat** keeps the conversation: voice turns are ordinary turns of the same thread, with the person's
  words stored as transcribed text.

## How it behaves (the owner's decisions, 2026-11-15)

- **The agent speaks back, and fills the form quietly.** A value the person said aloud in this conversation goes
  into its field without a card. Under the orb a short line says what was filled ("First name: Anna") with Undo,
  the same Undo the chat's result line has. Nothing is asked twice.
- **A card shows only when a confirmation is needed** (the CPO's list, 2026-11-15): a consent tick (always a
  tap); an action that cannot be undone or reaches other people (submit, cancel a booking: today's confirmation
  card); a value the person did not say (read from a document, worked out, taken from the page); replacing a
  value the person had typed by hand; a value the form refused; a real choice between options the agent cannot
  make itself. Everything else is filled and said: the voice reads the value back and the line with Undo covers a
  mishearing, so "easy to mishear" is not on the list.
- **How "quietly" is done without a second rule set.** The agent proposes changes exactly as in chat. The server
  marks a field-change card as `quiet` when every row in it passes the list above; the widget, in voice mode,
  applies a quiet card through the host's form at once and draws the line with Undo instead of the card. In chat
  nothing changes. The form still has the last word: a value it refuses comes back as a card.
- **Silent mode: the crossed-out microphone** (decided by the CPO from the owner's words, as the designer drew
  it). The microphone is off and the person types; the agent answers in short text under the orb and does not
  speak. It is one switch, kept for the conversation. No realtime session runs while it is on, so silent mode
  costs what the chat costs. "Quiet but still listening" would be a separate speaker control, not built now.

## The code

- Secrets on the host, given out by the CPO outside any chat. Compared in constant time; a few wrong tries per
  address a day, then refused.
- **One code per person** (decided): the host keeps a short list, a name with each code
  (`VOICE_CODES`). Then usage and spend are counted per person, one code can be withdrawn without touching the
  others, and a personal daily limit is possible on top of the shared one. It costs nothing extra to build this
  way from the start; a single shared code is the same list with one entry.
- `POST /voice/unlock {code}` answers with a signed pass that lives for the browser session. Every other voice
  route requires it. Without the secret set, the routes answer 404 and the widget shows no trace of the mode.
- The button "Activate Experimental Mode" sits in the widget's "+" menu on the demo pages only.

## What it costs

Rates (per 1M tokens): gpt-realtime-2.1 audio in $32, cached audio in $0.40, audio out $64, text in $4, cached
text in $0.40. gpt-realtime-2.1-mini: audio in $10, cached $0.30, audio out $20, text in $0.60, cached $0.06.
Speech is 600 tokens a minute heard and 1,200 tokens a minute spoken. Transcribing what was heard: $0.0045 a
minute. GPT-Live: $0.05 a minute flat.

The catch: a realtime session sends the whole conversation again with every response. OpenAI caches it "best
effort, not guaranteed", and the cached price is 80 times lower for audio. So the cost has a wide range that only
a measurement narrows, and the cap must be enforced from measured usage, not from the clock.

One demo conversation of 5 minutes, design B, estimate: the person speaks 2 minutes, the voice 1.5 minutes, about
15 requests, 25 model responses, a small instruction and one tool.

| | gpt-realtime-2.1 | gpt-realtime-2.1-mini | gpt-live-1 |
| --- | --- | --- | --- |
| New speech heard and spoken | $0.15 | $0.05 | |
| The conversation sent again, cached to uncached | $0.02 to $1.30 | $0.01 to $0.40 | |
| Voice, 5 minutes | **$0.20 to $1.45, expected about $0.35** | **$0.06 to $0.45, expected about $0.12** | **$0.25** |
| Voice, per minute | $0.04 to $0.29, expected $0.07 | $0.01 to $0.09, expected $0.025 | $0.05 |
| Dushes itself (Haiku, about 10 turns) and transcription | $0.03 to $0.10 | the same | the same |
| **5 minutes, all in, expected** | **about $0.45** | **about $0.20** | **about $0.33** |

Proposed limits for the experimental mode, separate from the chat demos' $3 + $2:

- a daily voice budget of **$4**, counted from the usage OpenAI reports for every response;
- a conversation ends at **5 minutes** or at **$0.75**, whichever comes first, with a spoken "that is the limit
  for one conversation";
- **one** voice conversation at a time, and 30 seconds of silence ends it;
- when the day's budget is used up the button says so and the chat works as always.

At the expected price that is 8 to 20 conversations a day depending on the voice model; at the worst case, five.

Before launch, estimate: my connection and bridge tests about $2; QA's benchmark (30 tasks of about a minute on
two voice models) about $4 to $6. **Up to $10 in total before the owner's first conversation**, each run priced
and agreed beforehand as always.

## What is measured before it is offered to the owner

QA's benchmark, paid for the agent only (the "speaker" is recorded clips made once with a free local voice):

- time from the end of speech to the first sound, and to the first useful sentence;
- task success: the field filled, the page read, the form opened only on a direct request, as in chat;
- cost per task and per minute, cached share included (this replaces the ranges above with numbers);
- interruption: speech stops within about half a second and the turn in progress is cancelled;
- English, Russian and Ukrainian at least.

## Who does what

| Part | Owner | Size | Waits for |
| --- | --- | --- | --- |
| The choice of voice (Realtime 2.1, mini, GPT-Live), the bridge, the routes, the limits | Tech Lead | L | the owner's yes to this estimate |
| The orb view, WebRTC in the widget, compact cards, loaded on demand | Design | L | the same, and the event list from the Tech Lead |
| The key on the host, the secret code, the voice budget in the day's counters | SRE | S | the owner sets the OpenAI key (the one Luna uses) |
| The page, marked experimental, with what is sent to OpenAI | Docs Lead | S | a working mode |
| The benchmark and the recorded clips | QA Lead | M | a working bridge |

## Risks and open questions

1. **Delay.** B adds the agent's 3 s to the voice's own. If the measured time to a useful sentence is over about
   5 s, the fast path is to let the voice answer small talk and "what can you do" itself and delegate the rest.
2. **Cost range.** Caching is not guaranteed; hence the per-conversation money limit, not only the time limit.
3. **Privacy.** In this mode the person's voice goes to OpenAI. The first screen of the mode says so; we keep the
   transcribed text only, as for any turn.
4. **Echo and noise** on laptop speakers: the browser's echo cancelling handles most of it; headphones are the
   honest advice for the demo.
5. **iPhone**: microphone and sound start only from a tap, which the Activate button gives; background tabs lose
   the connection.
6. **A code is weak protection** if it is ever typed on a shared screen: the limits above are the real guard.
7. **Decided**: values the person said are filled without a card; the card list above; silent mode is typing
   only; one code per person. **Open**: whether a spoken "yes" may answer a card that is shown. Proposed: yes,
   except a consent tick, which stays a tap.
8. **Open, with the owner**: the voice model and the budget.
