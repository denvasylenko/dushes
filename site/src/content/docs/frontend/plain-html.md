---
title: Plain HTML
description: The chat from one script tag on any page, with no build step.
---

`<agui-chat>` is a Web Component with no runtime dependencies (about 23 KB gzipped as one script), so it works on any page: server-rendered templates, Vue, Angular, or none at all.

```html
<agui-chat url="/agent/run" title="Assistant"></agui-chat>
<script src="agui-chat.iife.js"></script>
<script>
  const chat = document.querySelector('agui-chat')
  chat.use(AguiChat.formguide({
    getState: () => ({ config: window.formConfig, jsx_hash: window.jsxHash, form_id: 'loan_application' }),
    applyChanges: async (changes) => {
      const r = await fetch('/form/event', { method: 'POST', body: JSON.stringify({ changes }) })
      return (window.formConfig = await r.json())
    },
  }))
</script>
```

The script defines the element and `window.AguiChat` (`AguiChat.formguide`, `AguiChat.h`, `AguiChat.defineTheme`). Without the plugin it is a chat for any AG-UI endpoint.

## Floating, inline or full page

| `mode` | Looks like |
| --- | --- |
| `floating` (default) | a round button in the corner that opens a side panel |
| `inline` | fills its box: put it in a sidebar or a column next to the form |
| `page` | the whole window |

## Try every option live

The demo server serves [`examples/widget-html/`](https://github.com/denvasylenko/dushes/blob/main/examples/widget-html/index.html) at http://localhost:8000/examples/widget/: one script tag and a settings panel that switches mode, theme, scheme, language, typing, steps, dictation, attachments and quick replies while you chat.

Every attribute and event: [`<agui-chat>` API](../../reference/agui-chat/). Themes, tokens and parts: [The chat widget](../themes/).
