# Tasks

Nothing here starts before the owner agrees to the estimate in design.md.

## 1. Choose the voice
- [x] 1.1 Read GPT-Live's documentation; a connection test of gpt-live-1 (passed, $0.09; design.md)
- [x] 1.2 The voice is gpt-live-1 (the CPO's rule: use it if the check passes)

## 2. Host
- [x] 2.1a The codes, one per person (`VOICE_CODES`), the signed pass, the tries limit (`formguide.voice.Gate`)
- [x] 2.1b `POST /voice/unlock` and the pass on every voice route; routes absent when no code is set
- [x] 2.2 `POST /voice/session`: the call created with the host's key, the SDP answer returned
- [x] 2.3 The control connection: instructions, the one tool, usage, end of call
- [x] 2.4 The bridge: `ask_dushes` starts a Dushes turn; its events reach the widget; a short result is spoken
- [x] 2.5 Quiet filling: the server marks a field-change card `quiet` when every row is a value the person said,
      goes into an empty field and is not a consent (`formguide.voice.quiet`); the lab page applies it without a tap
- [x] 2.5c A spoken answer is short and makes no suggestion chips; every conversation is recorded (`log_dir`)
- [x] 2.5a A waiting card is asked aloud and answered by a spoken yes or no; a consent by the explicit yes to its
      question (the CPO, 2026-11-15); silence does not end a conversation under a card
- [ ] 2.5b Silent mode: no spoken output, short text answers, kept for the conversation
- [x] 2.6 Speaking over a turn in progress stops it and its voice (`interrupted`); a spoken yes or no answers a
      waiting card; the voice asks the card's question itself
- [x] 2.6a The answer goes to the voice sentence by sentence while it is written (`formguide.voice.ready`); offline
      only: how the provider speaks several pieces of one request is not checked live yet
- [x] 2.7a The limits as logic: the day's budget, a person's own, time and money per conversation, one at once,
      silence (`formguide.voice.Meter`)
- [x] 2.7b The limits enforced on a live session (the provider's usage events, closing the session)
- [x] 2.8 Offline tests with a scripted realtime session

- [x] 2.9a The bridge live with a recorded clip through the lab page (design.md, "The bridge, live")
- [ ] 2.9 The owner's own first conversation through the lab page (`/voice-lab/` on the docs host: the demo form with a
      microphone; not the product's interface)

## 3. Widget (Design)
- [ ] 3.1 The orb view, loaded on demand; the steps under it; compact cards and lines
- [ ] 3.1a A quiet card applied at once and drawn as a line with Undo; the crossed-out microphone (silent mode)
- [ ] 3.2 WebRTC through the host; Stop; back to chat with the conversation kept
- [ ] 3.3 "Activate Experimental Mode" in the "+" menu on the demo pages

## 4. Around it
- [ ] 4.1 SRE: the key, the code and the voice budget on the host
- [ ] 4.2 QA: recorded clips, the benchmark (first sound, task success, cost per task, interruption, three languages)
- [ ] 4.3 Docs: one page, marked experimental, with what is sent to OpenAI
