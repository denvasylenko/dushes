# Voice benchmark

What it answers: in the experimental voice mode, does a person who speaks get the same result as a person who types,
how long do they wait for a sound and for a useful sentence, what does a task cost, and does an interruption stop
the assistant. The agent behind the voice is the same Dushes agent as in chat (design B of
`openspec/changes/voice-mode/design.md`), so every existing rule keeps its meaning and its check.

Status: prepared, not run live. The set (`voice-v1.txt`, 50 scenarios), the clip recorder and the runner exist and a
mock run passes end to end; the live run waits for `formguide.voice`'s server-to-server transport and for the owner's
yes with a price (every paid voice test needs it; the CPO relays it). The speaker is a set of recorded clips, never
a second model: the API pays for the voice session and the agent, nothing else.

```bash
cd backend
uv run python scripts/voice_clips.py            # record the 66 clips with the Mac's voices (free; scripts/runs/voice-clips/)
uv run python scripts/voice_bench.py --mock     # the scripted voice over an offline demo: the plumbing, free
uv run python scripts/voice_bench.py --live --max-usd 1.40 --set evals/voice/voice-v1-en.txt   # not yet: the bridge, and the owner's yes
```

**English first** (the owner, 2026-11-15): the live passes run on the 32 English scenarios, `voice-v1-en.txt`
(44 spoken lines, 112 s of speech; 8 were added so that the small groups give a share: order 3, yes after an offer 4,
correction 4, interruption 4). The Russian and Ukrainian scenarios and clips stay recorded and are not run now.
Estimate for the English set: 44 lines of 20 to 25 s, 14.7 to 18.3 billed minutes, $0.73 to $0.92 a pass at $0.05 a
minute. The 15 seconds billed when a session opens are a minimum credited against the session's own duration, not a
charge on top (the Owner's two live sessions: 65.6 s reported as 65 s, 40.5 s as 39 s). Whether a session that fails
to start is charged them is not stated: the runner counts it as charged and reports the failed starts.
Decided (CPO, 2026-11-15): one pass now as the "before" point, stop sum $1.40, once the bridge has a
server-to-server audio path; the second pass comes after interruption and quiet filling are built and needs the
owner's new yes with a price. One session a scenario: a shared session would hear a scenario with the earlier ones
still in mind, and costs the same. An estimate from the price list, not a measurement.

A mock run's task results mean nothing (a one-line model answers); it proves the clips, the scenarios, the checks and
the report. Its billed time, 12.5 minutes for the whole set and 8.0 for the English one, is the
floor of a live pass: about $0.63 and $0.40 at $0.05 a minute, before the assistant's real speaking time.

## The speaker: recorded clips

`scripts/voice_clips.py` reads the scenarios and makes one WAV per spoken line with the Mac's own voices (`say`),
free and offline: Samantha (English), Milena (Russian), Lesya (Ukrainian). Its manifest gives each clip's text,
language, voice, rate and length.

- English, Russian and Ukrainian at least; one voice per language to start, a second voice and a faster rate for the
  second pass (a model that hears one synthetic voice well may not hear another).
- The text of every clip is known exactly, so what the voice model heard can be compared with it.
- Clips are sent in real time (a clip of four seconds takes four seconds), followed by their silence: the session's
  own end-of-speech detection is part of what is measured.
- A synthetic voice is cleaner than a person in a room. Results with it are an upper bound; the report says so. A
  small set of clips with added street noise is a later pass, not the first.

## Scenarios (voice-v1, 50)

Each scenario is a chat scenario's twin: a start (site, page, form), the clips in order, what to do with a card, and
the same `expect` keys as `evals/*.yaml`. Groups:

| Group | Count | What is said | What must happen |
| --- | --- | --- | --- |
| answer, do not open | 10 | a question (how, how much, can I, what do I need), from indirect-v1 | spoken answer with the fact, no page change, an offer |
| open on a direct order | 5 | "open the car insurance application" | the form opens at once |
| yes after an offer | 6 | a question, then "yes, open it" | the yes opens |
| fill by voice | 10 | a name, an age, a date said in words, a phone number, an amount, a choice, a bare number for an option with a unit ("36" for "36 months"), a choice with a detail nobody said | the field holds the value; every field-change card carries `quiet: true` (`quiet_cards`: applied with no tap); a detail the person did not say is asked, not guessed |
| hard to hear | 5 | an email spelled out, a VIN, a surname, a postcode, a mixed-language sentence | three outcomes, counted apart: the exact value filled (pass); asked to repeat and the field left empty (acceptable); a wrong value filled (fail) |
| confirmation needs a card | 4 | "I accept the terms", "submit it", a value from a document, replacing a typed value | a card is shown; a consent is ticked only by a tap |
| correction | 5 | "no, I said the fifteenth, not the fiftieth" | the field holds the corrected value |
| interruption | 5 | a second clip starts while the assistant speaks | the sound stops, the turn in progress is cancelled, nothing of it is applied |

Languages: every group has English; the first four groups also Russian and Ukrainian (about a third of the set).

## What is measured

Times, from the bridge's own clock (the runner does not guess from audio alone):

- **to the first sound**: from the end of the clip's speech to the first audible sample that comes back;
- **to the first useful sentence**: to the start of the first spoken sentence that carries the answer (it holds the
  scenario's key), not the "one moment" before it;
- **to the first step on screen**: to the first AG-UI event of the Dushes turn;
- for an interruption: from the start of the second clip to silence, and to the turn's stop.

Hearing: the transcript the session reports against the clip's text: word error rate, and exact match of the
entities that matter (numbers, dates, names, codes).

Task success, by code, the same checks as chat: the field's value, the page reached or not, `stays_put_on`, cards
shown and not shown, `card_results`, `never_says`. Plus two that only voice has: the spoken answer holds the fact
that the screen holds, and it states no number the agent's text does not have.

Cost: the session's connected seconds at the list price, and the agent's tokens from `run_stats`, per task and per
minute, separately and together.

## The bar (to propose to the CPO once the first pass exists)

No number is proposed before a measurement. The lines it will have: task success against the same scenarios typed;
the first sound and the first useful sentence at the median and the 90th percentile; entities heard right; consents
ticked by voice (must be none); interruptions that stopped the turn; dollars per task.

## What the bridge must give the runner

1. A server-to-server transport (WebSocket): the runner sends audio frames and receives audio and events, no browser.
2. A clock: every event with the bridge's monotonic time: end of speech detected, delegation created, the Dushes
   run started, the run's first text, the result handed to the voice, the first audio out, the response finished.
3. The transcript of what was heard and of what was spoken, as text events.
4. The Dushes turn's AG-UI events for the same conversation, and the thread, so the chat checks run unchanged; a
   start like a chat run's (site, page, form, state).
5. The usage: connected seconds from the session, `run_stats` of each turn, and a total at the end.
6. A fixed voice, language hint and end-of-speech settings per session, so two passes are comparable.
7. For an interruption: an event that the speech stopped and that the turn in progress was cancelled.
8. A stop sum and a session length limit the runner can set, and an offline mode with a scripted voice (it "hears"
   the clip's own text and "speaks" the result) so the runner and the scenarios are tested without a session.

## Spend (estimate, not a measurement)

At $0.05 a connected minute, a session billed for at least 15 seconds: a line of 20 to 25 seconds, so the 66
lines of the whole set are 21 to 27 minutes, $1.07 to $1.33 for the voice, and about $0.10 for the agent; the
English set $0.73 to $0.92. With a real-time voice model billed by tokens instead, the same
set is priced from its first ten scenarios before the rest runs. Every run has a stop sum and goes into QA's ledger.
