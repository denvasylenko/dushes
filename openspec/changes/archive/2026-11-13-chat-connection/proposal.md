# Proposal

## Why

The chat connects with a `url` and a static `headers` object, or a whole AG-UI agent object. Real hosts need more: a token that refreshes, cookies across domains, their own fetch (proxies, retries, logging, Electron, tests), a per-request hook, or their own transport (WebSocket, a worker, a mock). Worse, the formguide plugin's own requests (attachments, restoring a thread, feedback) use the global fetch without the host's headers, so behind authentication they fail with 401 while the chat itself works.

## What Changes

- `headers` takes an object or a function `({kind, url}) => headers`, sync or async, called before every request.
- New options: `credentials`, `fetch` (a fetch-compatible function), `request` (`({kind, url, init}) => {url, init}`: the last word on any request), and `transport` (`(input, {signal}) => AsyncIterable<AguiEvent>`: the run without HTTP). The `agent` property stays and works as before.
- `kind` names the request: `run`, `attachments`, `thread`, `feedback`, or a plugin's own.
- `ChatApi.request(kind, url, init)` sends a request through the same connection; the formguide plugin uses it for attachments, thread restore and feedback, so headers, credentials and fetch apply to every call.
- A failing `headers`, `fetch` or `request` is a run error like any other: a readable message with Try again, the raw text in `agui:error`.

## Capabilities

### Modified Capabilities
- `chat-widget`: connection options and `ChatApi.request`.
- `chat-widget-formguide`: the plugin's requests go through `ChatApi.request`.

## Impact

- Widget: `src/transport.ts` (`runHttp` takes a fetch), `src/element.ts` (`request`, transport choice), `src/types.ts`, `src/formguide/index.ts` and `pickers.ts` (plugin requests), tests.
- Docs: `site/` frontend/chat-widget (Connection section, "Every option"), reference/agui-chat, an authentication example.
- No backend change.
