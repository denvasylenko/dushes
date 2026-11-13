# Design

Mini-brief (ui-craft)
1. Who and why: a user whose browser cannot or may not recognise speech, dictating a message.
2. Main action: stop the recording (the microphone, now a stop button); cancel is secondary.
3. Taps: mic, speak, mic again, check, send: the same as browser dictation, one wait more.
4. States: recording (wave + timer), transcribing (dots + "Transcribing…"), empty result ("Didn't catch that"), error ("Couldn't transcribe the recording" + Try again), denied (the existing hint), too long (stops at max_seconds and transcribes).
5. Phone: the wave fills the input row, the stop button stays under the thumb at the right, cancel at the left where the paperclip was.

Like iOS Messages' dictation and Voice Memos: grey bars that scroll from the right with the voice level, a monospaced timer, and the same red stop control as the browser's dictation.

Server: faster-whisper loads its model lazily on the first request (downloaded once to the Hugging Face cache) and runs in a worker thread; `language` from the request (the chat's language) skips detection. A `module:function` provider gets `(bytes, filename, language)` and returns text (sync or async).
