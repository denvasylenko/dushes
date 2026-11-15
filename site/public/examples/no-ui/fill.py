"""Fill a form from a service: no chat, no browser. Plain words in, field values out."""
import json
import uuid

import httpx


def fill(client: httpx.Client, text: str, state: dict, apply) -> dict:
    """text: what goes in the form, in plain words.
    state: the form's state, the same object a page sends: {config, jsx_hash, form_id}.
    apply(changes): puts {name: value} into your form and returns its new config."""
    thread = str(uuid.uuid4())
    messages = [{"role": "user", "content": text}]
    body = {"threadId": thread, "messages": messages, "state": state}
    filled: dict = {}
    for _ in range(5):                                   # the agent proposes values one card per request
        card = None
        with client.stream("POST", "/run", json=body, headers={"Accept": "text/event-stream"}) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line.startswith("data:"):
                    continue
                event = json.loads(line[5:])
                if event["type"] == "RUN_ERROR":
                    return {"status": "error", "message": event.get("message"), "values": filled}
                if event["type"] == "CUSTOM" and event.get("name") == "on_interrupt":
                    value = event["value"]               # the card the chat would show
                    card = json.loads(value) if isinstance(value, str) else value
        if card is None:                                 # the run ended with nothing to answer: finished
            return {"status": "done", "values": filled}
        if card.get("type") != "set_fields":             # a question or a confirmation: a person's call
            return {"status": "needs_input", "question": card.get("question"), "values": filled}
        changes = {c["name"]: c["value"] for c in card["changes"]}
        filled.update(changes)
        state = {**state, "config": apply(changes)}      # your form takes the values
        body = {"threadId": thread, "messages": messages, "state": state,   # and the card is answered: accepted
                "forwardedProps": {"command": {"resume": {"accepted": True, "config": state["config"]}}}}
    return {"status": "needs_input", "question": "The agent kept proposing changes.", "values": filled}


if __name__ == "__main__":
    # your own form: its state for the agent, and how it takes values
    from my_forms import loan   # .state() -> {config, jsx_hash, form_id}; .apply(changes) -> the new config

    with httpx.Client(base_url="http://localhost:8000/agent", timeout=120) as client:
        result = fill(client, "Car loan for Alex Morgan, alex.morgan@example.com, $28,000 over 36 months.",
                      loan.state(), loan.apply)
    print(json.dumps(result, indent=2))
