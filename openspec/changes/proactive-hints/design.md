# Design

## Context

Quick replies (`suggestions.py`) are already made after a turn by a cheap model with a timeout and never enter the history. The widget knows the form's focus and errors through the form plugin.

## Goals / Non-Goals

**Goals:** one chip at a stuck moment, at the cost of one cheap call.

**Non-Goals:** no popups, sounds or opened chat panels; no tracking or analytics of the user's behaviour.

## Decisions

- **A moment is a run without a message.** It reuses the endpoint, auth and limits; the server takes a short path (no graph) straight to the suggestion maker.
- **Fixed text first.** `idle_field` with a glossary note can use a fixed template ("What goes in <label>?") with no model call; the cheap model is used for errors and leaving.
- **The widget decides when, the server decides whether.** Detection is local and cheap; the server applies `enabled`, `kinds` and the per-page limit, so a host can tune it without a release of the page.

## Risks / Trade-offs

- [Feels like surveillance] → off by default, one chip per page, nothing recorded until tapped; the docs say so.
- [Extra load] → moments are debounced in the widget and rate-limited per thread on the server.
