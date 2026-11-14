# Proposal

Status: proposal only (backlog); after the live landing demo.

## Why

The widget gets a "+" menu and "/" in the composer listing a host's commands. Today a host could only pass them as a frontend option, so the same list is kept in two places (the page and the agent's config) and drifts. The owner wants one place: the backend config, with the frontend option as an override.

## What Changes

- `commands:` in formguide.yaml (and `FormGuideConfig.commands`, `Dushes(commands=...)` in Python), a list:
  ```yaml
  commands:
    - name: status                    # /status; [a-z0-9_-]{1,32}, unique
      description: Check my application's status
      args: [{name: ref, hint: "Application number", required: false}]
      run: {tool: check_status}       # call a host tool (SiteTool or a form tool) with the args
    - name: rates
      description: Show today's rates
      run: {page: /rates}             # open a page (the site map's path)
    - name: help
      description: What can you do?
      run: {prompt: "What can you help me with on this page?"}   # send this text as the user's message
    - name: summarize
      description: Summarize my answers
      run: {skill: summarize_form}    # run a skill
  ```
  Exactly one of `tool`, `page`, `prompt`, `skill`. Commands may be scoped: `forms: [loan_application]` or `pages: ["/loans/*"]`. An optional `icon` is one of the widget's built-in names (calendar, call, route, web, share, copy, chat, check, clock, pin, star, person, tag, info, doc, search, settings, plus); an unknown name means no icon, never a URL. Keyboard shortcuts are not configured here: they belong to the widget's own option.
- **To the widget**: the restore response (`GET /threads/{id}`, `/site/threads/{id}`) and every run's STATE_SNAPSHOT carry `commands: [{name, description, args, icon?}]` for the current form or page, so page-scoped commands follow the visitor between pages; never `run`, so the page learns nothing about the host's tools. The widget's own `commands` option (`{name, description, args?, icon?, shortcut?, hidden?}`) merges with the list by name.
- **Arguments are free text after the name**, as in Claude and Slack ("/status A-1029"): the widget maps the words to the declared args in order (the last arg takes the rest of the line) and shows each missing arg's `hint` as ghost text; it does not send while a required arg is empty. The server validates the args again.
- **Running one**: the widget sends `forwardedProps.command_call = {name, args}` with the message text it shows ("/status A-1029"). The server validates the name and args against the config, then: `prompt` runs as a user turn; `page` emits the existing navigate directive; `tool` and `skill` run with the same rules as when the agent calls them (`confirm_tools`, `confirm=True`, Undo from host-actions), and the agent then answers about the result. An unknown command or bad args get one short answer, no tool call.
- The config check (`formguide.config.KEYS`, the docs drift test) covers the new key.

## Capabilities

### New Capabilities
- `host-commands`: declaring commands, sending them to the widget, running them.

## Impact

`formguide/config.py`, `agui.py` (command_call), `guide.py` and `site/guide.py` (restore and run), docs (configuration reference, the widget's commands page), the widget (the "+" menu and "/" list: widget designer).
