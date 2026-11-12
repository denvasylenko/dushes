## ADDED Requirements

### Requirement: Connection options
The chat SHALL accept `headers` as an object or as a function of `{kind, url}` (sync or async) called before every request, plus `credentials`, `fetch` (used instead of the global fetch) and `request` (a function of `{kind, url, init}` returning the `{url, init}` to send). `kind` SHALL be `run` for a run and the plugin's name for others (`attachments`, `thread`, `feedback`).

#### Scenario: A refreshed token
- **WHEN** `headers` is `async () => ({Authorization: 'Bearer ' + await getToken()})`
- **THEN** every run and every plugin request carries the current token

#### Scenario: A custom fetch
- **WHEN** `fetch` is set to the host's function
- **THEN** the chat sends every request through it and never calls the global fetch

### Requirement: Own transport
The chat SHALL accept `transport`, a function of the run input and `{signal}` returning an async iterable of AG-UI events, and use it instead of HTTP; when it is not set, an `agent` object, and otherwise `url`, SHALL be used as before. A failure of the transport, `headers`, `fetch` or `request` SHALL end the run with the usual readable error.

#### Scenario: A mock transport
- **WHEN** `transport` yields RUN_STARTED, a text message and RUN_FINISHED
- **THEN** the chat shows the text and makes no network request

### Requirement: Requests through the chat's connection
`ChatApi.request(kind, url, init)` SHALL send a request with the chat's headers, credentials, fetch and request hook, so plugins reach the server the same way as runs.

#### Scenario: A plugin request
- **WHEN** a plugin calls `chat.request('thread', url)` and `headers` adds an Authorization header
- **THEN** the request carries that header
