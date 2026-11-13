# Proposal

## Why

Dictation in the chat uses the browser's own speech recognition. Some browsers do not have it (Firefox), and some companies block it (the browser's recognition service, or audio leaving to it), so the microphone is missing or fails. A host may also not want speech to leave for a browser vendor's service. A local Whisper model on the host's server covers those cases for free.

## What Changes

- **Server**: an optional `transcription` config (`provider: faster_whisper` by default, with `model`, `device`, `compute_type`, `language`, `max_seconds`, `max_bytes`; `provider: openai` or `module:function` for a host's own). `POST /transcribe` (multipart `file`, optional `language`) returns `{text, language}`; 501 when transcription is not configured, 413 when the recording is too large. The site router serves the same endpoint. The `transcribe` extra installs faster-whisper.
- **Widget**: `dictation: 'browser' | 'server' | 'auto'` (default `browser`, as today) and `transcribeUrl` (default: `transcribe` next to the run URL). In server mode the microphone records: the input is replaced by a live wave with a timer and a cancel button; tapping the microphone again shows "Transcribing…", then the text lands in the input to check and send. `auto` uses the browser's recognition where it works and records for the server where it is missing or blocked. Esc or the cancel button drop the recording; a failed transcription says so in plain words with "Try again".

## Capabilities

- `http-api`: `POST /transcribe` and the `transcription` config.
- `chat-widget`: server-side dictation.
