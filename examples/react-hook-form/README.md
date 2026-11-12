# react-hook-form + formguide

An ordinary [react-hook-form](https://react-hook-form.com) form (a short car loan application) with the formguide chat next to it. The form knows nothing about the chat: the glue is a schema and one hook.

```tsx
import { AguiChat } from '@formguide/agui-chat/react'
import { useFormguide, type FormSchema } from '@formguide/agui-chat/react-hook-form'

const form = useForm()
const { plugins, ready } = useFormguide(form, schema, { onReveal: setTab })
{ready && <AguiChat url="/agent/run" mode="inline" plugins={plugins} />}
```

The schema lists the sections and fields with labels, types and options; rules (`options`, `visible`, `disabled`, `required`) may be functions of the current values. See `src/App.tsx`.

## Run

Start the demo server (backend, port 8000), then either:

```bash
npm install && npm run dev      # http://localhost:5175, proxies /agent to :8000
```

or build it and open it from the demo server:

```bash
npm install && npm run build    # http://localhost:8000/examples/react-hook-form/
```

The demo server only mounts the build if it existed at start-up: restart it after the first build.
