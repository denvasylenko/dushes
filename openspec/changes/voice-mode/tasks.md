# Tasks

Nothing here starts before the owner agrees to the estimate in design.md.

## 1. Choose the voice
- [ ] 1.1 Read GPT-Live's documentation in full; one connection test of each candidate (gpt-realtime-2.1, its mini, gpt-live-1)
- [ ] 1.2 Decide the voice with the CPO from delay, languages and measured price

## 2. Host
- [ ] 2.1 The codes, one per person (`VOICE_CODES`): `POST /voice/unlock`, the pass, the tries limit, usage per
      person; routes absent when no code is set
- [ ] 2.2 `POST /voice/session`: the call created with the host's key, the SDP answer returned
- [ ] 2.3 The control connection: instructions, the one tool, usage, end of call
- [ ] 2.4 The bridge: `ask_dushes` starts a Dushes turn; its events reach the widget; a short result is spoken
- [ ] 2.5 Quiet filling: the server marks a field-change card `quiet` by the agreed list; a consent is never quiet
- [ ] 2.5a An open card answered by spoken words; consent by tap only
- [ ] 2.5b Silent mode: no spoken output, short text answers, kept for the conversation
- [ ] 2.6 Interruption stops the turn in progress
- [ ] 2.7 Limits: the day's voice budget, time and money per conversation, one conversation at once, silence
- [ ] 2.8 Offline tests with a scripted realtime session

## 3. Widget (Design)
- [ ] 3.1 The orb view, loaded on demand; the steps under it; compact cards and lines
- [ ] 3.1a A quiet card applied at once and drawn as a line with Undo; the crossed-out microphone (silent mode)
- [ ] 3.2 WebRTC through the host; Stop; back to chat with the conversation kept
- [ ] 3.3 "Activate Experimental Mode" in the "+" menu on the demo pages

## 4. Around it
- [ ] 4.1 SRE: the key, the code and the voice budget on the host
- [ ] 4.2 QA: recorded clips, the benchmark (first sound, task success, cost per task, interruption, three languages)
- [ ] 4.3 Docs: one page, marked experimental, with what is sent to OpenAI
