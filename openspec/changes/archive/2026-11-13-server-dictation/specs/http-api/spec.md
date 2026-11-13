## ADDED Requirements

### Requirement: Server-side transcription
With a `transcription` section in the config, `POST /transcribe` SHALL accept a multipart `file` (audio as the browser records it) and an optional `language`, and return `{text, language}`. The default provider SHALL be a local faster-whisper model, loaded on the first request; `provider: openai` and `provider: "module:function"` SHALL be supported. Without the section the endpoint SHALL answer 501; a file over `max_bytes` SHALL get 413.

#### Scenario: A short recording
- **WHEN** the page posts a 5-second recording with `language: ru`
- **THEN** the answer is `{text: "...", language: "ru"}`

#### Scenario: Not configured
- **WHEN** the config has no `transcription`
- **THEN** `POST /transcribe` answers 501

### Requirement: Transcription on the site router
The site router SHALL serve `POST /transcribe` with the form guide's transcription, so a site chat dictates the same way.

#### Scenario: The site chat
- **WHEN** the site page posts a recording to `/site/transcribe`
- **THEN** it gets the same answer as `/agent/transcribe`
