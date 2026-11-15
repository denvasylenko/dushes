# Proposal

## Why

The owner (through the CPO, 2026-11-15): Dushes should be something you can simply talk to, as in the ChatGPT app.
On every demo page, behind a code only he has ("Activate Experimental Mode"), the chat gives way to a pulsing orb
with the steps of the work under it; he speaks, and the agent answers aloud and with small widgets or short
see-through lines of text. "Clearly with the OpenAI model."

Today the widget has dictation only: speech becomes text in the message box and the answer is read as text.

## What Changes

- **An experimental voice mode** in `<agui-chat>` on the Dushes demo pages, the form-filling page first. Speech in,
  speech out, with interruption ("barge-in"), Stop, and a way back to the chat with the conversation kept.
- **By default the agent speaks and fills the form quietly** (the owner, 2026-11-15): what the person said goes
  into the fields without a card, with a short line and Undo; a card appears only when a confirmation is needed.
- **Silent mode** (the crossed-out microphone): the microphone is off, the person types, and the agent answers
  in short text instead of speaking.
- **Behind a code.** The code is a secret on the host. Without it nothing on any page changes and no voice route
  answers.
- **OpenAI Realtime is the voice, Dushes stays the agent** (the recommended design, see design.md): the realtime
  model listens and speaks; everything the person asks goes to the existing agent on our server, which fills
  fields, opens forms under the "answer first" gate, reads pages and documents, and shows its cards. No business
  rule moves into the voice model.
- **Its own limits**: a daily budget separate from the chat demos, a time limit per conversation, a limit on
  conversations at once, all enforced on the server from measured usage.
- **In the package, for every consumer** (the owner's go, 2026-11-15): the web widget and the Swift client both
  get the mode, so Herefront and the cabinet use it through the package. Each product keeps its own agent model
  and its own daily voice budget ($5 each: the Dushes stand, Herefront iOS, Herefront web).

## Impact

- New in the package (`backend/formguide/voice`): the routes to unlock the mode, start a voice conversation and
  end it; the bridge between the voice session and a run; the limits and the codes. The docs host mounts it; so
  can any host. In the agent: a `quiet` mark on field-change cards and a way to answer an open card with words.
- The Swift client (`packages/agui-chat-swift`, the iOS Tech Lead): the same mode against the same routes.
- The widget (`packages/agui-chat`, the designer's): the orb view, the WebRTC connection, compact cards and lines.
  It does not fit the main file's size budget, so it loads on demand when the mode is switched on.
- Docs (Docs Lead): one page, marked experimental. QA: a voice benchmark (time to first sound, task success, cost
  per task) that pays for the agent only: the "speaker" is a set of recorded clips, not a second model.
- Money: see design.md, "What it costs". Nothing is spent before the owner agrees to the estimate.
