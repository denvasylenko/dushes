"""Voice mode, the part with no network: the codes (one per person), the pass, the limits (openspec/changes/voice-mode)."""
from __future__ import annotations

import pytest

from formguide.voice import TRIES_PER_DAY, Gate, Meter, VoiceConfig, parse_codes


class Clock:
    def __init__(self, t: float = 1_800_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t


CODES = {"anna": "anna-code-0001", "ben": "ben-code-00002"}


def test_without_a_code_there_is_no_voice_mode():
    assert not VoiceConfig().enabled and not VoiceConfig.from_env({}).enabled
    cfg = VoiceConfig.from_env({"VOICE_CODES": "anna=anna-code-0001, ben=ben-code-00002", "VOICE_DAY_USD": "5",
                                "VOICE_MAX_SECONDS": "120"})
    assert cfg.enabled and cfg.codes == CODES and cfg.day_usd == 5 and cfg.max_seconds == 120 and cfg.model == "gpt-live-1"


def test_a_weak_or_ambiguous_list_of_codes_is_refused():
    for bad in ("anna", "anna=short", "an na=anna-code-0001", "anna=anna-code-0001,anna=other-code-01",
                "anna=same-code-0001,ben=same-code-0001"):
        with pytest.raises(ValueError):
            parse_codes(bad)
    assert parse_codes("") == {} and parse_codes(" , ") == {}


def test_a_code_gives_a_pass_that_names_its_person():
    clock = Clock()
    gate = Gate(VoiceConfig(codes=CODES), clock)
    assert gate.unlock("nope-nope-nope") is None
    who, token = gate.unlock("  ben-code-00002 ")
    assert who == "ben" and gate.person(token) == "ben"
    assert gate.person(None) is None and gate.person("ben.9999999999.forged") is None
    assert gate.person(token.replace("ben.", "anna.")) is None          # a pass cannot be renamed
    assert Gate(VoiceConfig(codes=CODES), clock).person(token) is None   # another host's secret does not accept it
    clock.t += 13 * 3600
    assert gate.person(token) is None                                    # it expires


def test_a_withdrawn_code_ends_its_passes_and_leaves_the_others():
    cfg = VoiceConfig(codes=dict(CODES), secret="s" * 32)
    gate = Gate(cfg, Clock())
    _, anna = gate.unlock("anna-code-0001")
    _, ben = gate.unlock("ben-code-00002")
    del cfg.codes["anna"]
    assert gate.person(anna) is None and gate.person(ben) == "ben"


def test_wrong_tries_are_limited_per_address_and_day():
    clock = Clock()
    gate = Gate(VoiceConfig(codes=CODES), clock)
    for _ in range(TRIES_PER_DAY):
        assert gate.unlock("wrong-wrong-wrong", "1.2.3.4") is None
    assert gate.unlock("anna-code-0001", "1.2.3.4") is None              # even the right code, from that address
    assert gate.unlock("anna-code-0001", "5.6.7.8") is not None          # another address is not punished
    clock.t += 24 * 3600
    assert gate.unlock("anna-code-0001", "1.2.3.4") is not None          # the next day


def test_one_conversation_at_a_time_and_its_three_ends():
    clock = Clock()
    meter = Meter(VoiceConfig(codes=CODES, max_seconds=300, max_usd=0.75, silence_seconds=30), clock)
    assert meter.refusal("anna") is None
    meter.start("t1", "anna")
    assert meter.refusal("ben") == "busy"
    clock.t += 20
    meter.report("t1", seconds=20, heard=True)
    assert meter.over("t1") is None
    clock.t += 31
    assert meter.over("t1") == "silence"                                 # nobody spoke for half a minute
    meter.report("t1", heard=True)
    meter.report("t1", agent_usd=0.72)                                   # the agent's own turns count too
    assert meter.over("t1") == "money"
    assert round(meter.end("t1", seconds=52), 4) == round(52 / 60 * 0.05 + 0.72, 4)
    meter.start("t2", "ben")
    clock.t += 300
    assert meter.over("t2") == "time"                                    # five minutes, by the clock when no report came


def test_the_days_budget_counts_reported_seconds_and_resets():
    clock = Clock()
    meter = Meter(VoiceConfig(codes=CODES, day_usd=0.10, person_day_usd=0.06, max_seconds=10_000, max_usd=100,
                              silence_seconds=10_000), clock)
    meter.start("t1", "anna")
    clock.t += 60
    meter.report("t1", seconds=30)        # a late report never makes the spend smaller than the clock says
    assert round(meter.spent(), 3) == 0.05 and round(meter.spent("anna"), 3) == 0.05
    meter.report("t1", seconds=72)        # a snapshot, not an addition
    meter.report("t1", seconds=72)
    assert round(meter.end("t1", seconds=72), 3) == 0.06
    assert meter.refusal("anna") == "person_day" and meter.refusal("ben") is None
    meter.start("t2", "ben")
    clock.t += 60
    assert meter.over("t2") == "day" and meter.end("t2") > 0             # the stand's budget ends an open conversation
    assert meter.refusal("ben") == "day"
    clock.t += 24 * 3600
    assert meter.refusal("anna") is None and meter.spent() == 0          # a new day
