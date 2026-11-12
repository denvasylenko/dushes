# Tasks

## 1. Connection

- [x] 1.1 Types: `headers` object or function, `credentials`, `fetch`, `request`, `transport`; `ChatApi.request`
- [x] 1.2 `runHttp` takes a fetch; `element.request(kind, url, init)` applies headers, credentials, the request hook and the fetch
- [x] 1.3 Transport choice: `transport`, else `agent`, else HTTP; failures as readable run errors

## 2. Plugin

- [x] 2.1 Attachments, thread restore and feedback through `chat.request`

## 3. Tests and docs

- [x] 3.1 Tests: dynamic headers on runs and plugin requests, custom fetch, request hook, credentials, transport, a failing headers function
- [x] 3.2 `site/`: Connection section in frontend/chat-widget with an auth example, the "Every option" list, reference/agui-chat
- [x] 3.3 Validate, English check, widget tests and build, site build; archive
