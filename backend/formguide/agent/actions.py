"""Which actions the agent has in a run.

Three inputs decide it:
- the config (`actions: {ask_user: true, request_file: false, ask_documents: auto, ...}`): what this
  deployment allows;
- `auto` rules: ask_documents only when the form has business documents; request_file and
  extract_from_attachment only when attachments are enabled;
- the client's capabilities (`forwardedProps.capabilities`): what this UI can render. When the client
  sends no list, everything the config allows stays on (older clients).

The read-only form tools, propose_changes and use_skill are always on.
"""
from __future__ import annotations

from collections.abc import Iterable

# actions that can be switched off, and their defaults
ACTIONS: dict[str, object] = {
    "ask_user": True, "request_file": "auto", "confirm_action": True, "focus_field": True,
    "review_form": True, "ask_documents": "auto", "extract_from_attachment": "auto",
}

# what an action needs the client to render (checked only when the client sends capabilities). A client
# that lists a variant ("ask.details") renders its base card ("ask") too. focus_field draws no card.
# actions a host turns on per run, never the config: hand_back exists only when the form agent works under the
# site assistant (SiteGuide adds the capability "hand_back"); off for every other client, old ones included
HOST_ACTIONS = ("hand_back",)

ACTION_CAPS: dict[str, str] = {
    "ask_user": "ask", "request_file": "upload", "confirm_action": "confirm", "review_form": "review",
}

# payload variants a client can render; a variant it does not list is stripped or refused
VARIANTS = ("ask.details", "ask.compare", "ask.search", "ask.date", "ask.slots", "ask.range", "ask.multi",
            "ask.address", "set.consent", "set.issues", "set.document", "sources", "confirm.receipt",
            "upload.camera", "feedback")


def parse_config(raw: object) -> dict[str, object]:
    """`actions` from YAML or code -> {action: True | False | "auto"} for every action."""
    out = dict(ACTIONS)
    if raw in (None, {}):
        return out
    if not isinstance(raw, dict):
        raise ValueError("actions must be a mapping of action: true | false | auto")
    unknown = set(raw) - set(ACTIONS)
    if unknown:
        raise ValueError(f"actions: unknown key(s) {sorted(unknown)}; allowed: {sorted(ACTIONS)}")
    for k, v in raw.items():
        if v not in (True, False, "auto"):
            raise ValueError(f"actions.{k} must be true, false or auto")
        out[k] = v
    return out


def capabilities(raw: object) -> frozenset[str] | None:
    """`forwardedProps.capabilities` -> a set, or None when the client sent no list."""
    if not isinstance(raw, (list, tuple)):
        return None
    return frozenset(str(x) for x in raw if isinstance(x, (str, int)))


def resolve(config: dict[str, object], *, has_documents: bool, attachments: bool,
            caps: frozenset[str] | None) -> frozenset[str]:
    """The actions on in this run."""
    on = set()
    for name, v in config.items():
        if v == "auto":
            v = has_documents if name == "ask_documents" else attachments
        if not v:
            continue
        if caps is not None and name in ACTION_CAPS and not has(caps, ACTION_CAPS[name]):
            continue
        on.add(name)
    on.update(a for a in HOST_ACTIONS if caps is not None and a in caps)
    return frozenset(on)


def has(caps: frozenset[str], card: str) -> bool:
    """The client renders a base card: it lists it, or one of its variants ("ask.details" -> "ask")."""
    return card in caps or any(c.startswith(card + ".") for c in caps)


def can(caps: frozenset[str] | None, variant: str) -> bool:
    """Whether the client renders a payload variant (all of them when it sent no list)."""
    return caps is None or variant in caps


def off(actions: Iterable[str]) -> frozenset[str]:
    """The switchable actions that are not in `actions`."""
    return (frozenset(ACTIONS) | frozenset(HOST_ACTIONS)) - frozenset(actions)
