## ADDED Requirements

### Requirement: Dictation on the server
`dictation: 'server'` SHALL make the microphone record audio instead of using the browser's recognition: the input is replaced by a live wave with a timer and a cancel button; tapping the microphone again SHALL show "Transcribing…", post the recording to `transcribeUrl` (default: `transcribe` next to the run URL) through the chat's connection, and put the text into the input without sending it (unless `micAutoSend`).

#### Scenario: Dictating through the server
- **WHEN** the user taps the microphone, speaks and taps it again
- **THEN** the chat shows "Transcribing…" and then the recognised text in the input

### Requirement: Cancelling and failures of server dictation
Esc or the cancel button SHALL drop a recording without sending it. An empty result SHALL say nothing was caught; a failed transcription SHALL say so in plain words with "Try again", which posts the same recording again.

#### Scenario: The server is down
- **WHEN** the transcription request fails
- **THEN** the hint says the recording could not be transcribed and offers Try again

### Requirement: Dictation that falls back
`dictation: 'auto'` SHALL use the browser's recognition where it exists and works, and record for the server where it is missing or blocked (the recognition service refused or unreachable); the microphone SHALL show whenever either way is possible.

#### Scenario: A browser without recognition
- **WHEN** the browser has no SpeechRecognition and `dictation` is `auto`
- **THEN** the microphone shows and records for the server
