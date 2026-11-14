# Proposal

Status: proposal only (backlog). Part of `core-and-capabilities` (the Do and Know capabilities).

## Why

Hosts want to plug in tools they already have as MCP servers (a CRM, a booking system, a document store) without writing a SiteTool per call. This belongs in the host's backend config, never in the end user's chat: the end user cannot add a server or a credential.

## What Changes

- `mcp_servers:` in formguide.yaml:
  ```yaml
  mcp_servers:
    crm:
      transport: http                      # http (streamable HTTP) | stdio
      url: https://crm.internal/mcp
      headers: {Authorization: "Bearer ${CRM_MCP_TOKEN}"}   # from the environment, never the YAML itself
      tools: [find_customer, get_order]    # an allowlist: required; tools not named are never exposed
      read_only: true                      # default: every allowed tool is treated as read-only
      confirm: [cancel_order]              # tools with effects: always a confirmation card first
      agents: [site, form]                 # which agents get them (default: site)
      timeout_s: 15
      max_result_chars: 8000
  ```
- At start-up the server lists each server's tools and exposes only the allowlisted ones to the chosen agents, with their MCP schemas, named `<server>__<tool>`. A server that is down is logged, and its tools are left out until it answers; the agent never sees a dead tool.
- A tool with effects must be listed in `confirm` (or `read_only: false` with `undo` through host-actions); otherwise the server refuses to start with that tool allowed while it declares effects (MCP's `readOnlyHint` / `destructiveHint` are read but not trusted alone).

## Security notes

- **Prompt injection through tool output.** An MCP result is data from outside the business's control (a customer's note in the CRM can say "ignore your rules"). Results reach the model inside a delimited block marked as tool data; the prompts already treat tool data as facts, never instructions, and that rule is extended to name MCP results. A result never changes the tool set, the confirmation rules or the allowlist. Results are cut to `max_result_chars`.
- **Credentials.** A server gets only what its entry gives it: headers from environment variables, resolved at start-up, never logged, never shown to the model or sent to the widget. No end user's token is passed through by default; a host that needs per-user access passes a short-lived, scoped token by a hook (`headers_for(ctx)`), never the user's session cookie.
- **stdio servers** run as a child process with the host's rights: allowed only when the host sets `transport: stdio` explicitly, with a fixed command, no shell, and a clean environment (only the variables listed in `env`).
- **Least privilege.** The allowlist is required, read-only is the default, and side effects need a confirmation card in the chat. Every MCP call is in run_stats and the OpenTelemetry span (tool name, ms, error), never its arguments or result.
- **Network.** HTTP servers are called only at their configured URL; redirects to another host are refused.

## Capabilities

### New Capabilities
- `mcp-tools`: MCP servers as the agents' tools under the allowlist, read-only by default, with confirmation for effects.

## Impact

A new optional extra (`formguide[mcp]`, the official MCP Python SDK), `formguide/config.py` (KEYS), the agent's tool set, the prompts' tool-data rule, docs (configuration reference, a guide under agents/shared), Security review before it ships.
