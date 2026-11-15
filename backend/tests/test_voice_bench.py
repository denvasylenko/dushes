"""The voice benchmark's own parts (scripts/voice_bench.py, voice_clips.py): the set, the clips' manifest, what is
measured about hearing, and a mock run. No session, no key, no audio is recorded here."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import evals  # noqa: E402
import voice_bench as vb  # noqa: E402
import voice_clips as vc  # noqa: E402

SET = vb.SCENARIOS / "voice-v1.txt"


def test_the_set_loads_and_covers_the_groups_and_three_languages():
    scs = [evals.load_scenario(vb.SCENARIOS / f"{n}.yaml") for n in SET.read_text().split()]
    assert len(scs) == 40 and all(s.tags[0] == "voice" and s.scripted for s in scs)
    groups = {g: sum(s.tags[1] == g for s in scs) for g in ("answer", "order", "offer_yes", "fill", "hard", "card", "fix", "interruption")}
    assert groups == {"answer": 10, "order": 4, "offer_yes": 3, "fill": 8, "hard": 5, "card": 4, "fix": 3, "interruption": 3}
    langs = {lang: sum(s.tags[2] == lang for s in scs) for lang in vc.LANGS}
    assert langs["en"] >= 20 and langs["ru"] >= 8 and langs["uk"] >= 6
    assert all(len(s.scripted) == 2 for s in scs if s.tags[1] == "interruption")     # the second clip is the cut-in
    consent = [s for s in scs if "accept_terms" in s.fields]
    assert consent and all(s.fields["accept_terms"] is False for s in consent)      # a spoken yes never ticks a consent


def test_every_spoken_line_has_one_clip_in_the_manifest():
    items = vc.manifest(SET, 1)
    assert len(items) == sum(len(evals.load_scenario(vb.SCENARIOS / f"{n}.yaml").scripted) for n in SET.read_text().split())
    assert {i["voice"] for i in items} == set(vc.VOICES.values()) and all(i["rate"] == vc.RATES[1] for i in items)
    assert vc.clip_id("en", "hello", 175) != vc.clip_id("en", "hello", 215) != vc.clip_id("ru", "hello", 215)   # a pass records its own clips
    faster = vc.manifest(SET, 2)
    assert [i["text"] for i in faster] == [i["text"] for i in items] and faster[0]["clip"] != items[0]["clip"]


def test_hearing_is_measured_by_words_and_by_the_things_that_matter():
    assert vb.wer("book me a haircut", "book me a haircut") == 0
    assert vb.wer("book me a haircut", "book me the haircut") == 0.25
    assert vb.wer("my age is thirty four", "") == 1
    assert vb.entities("the VIN of my Toyota is 555 and I am 34") == ["555", "34", "VIN", "Toyota", "I"]
    assert vb.entities_kept("Anna Kowalczyk, 34", "anna kovalchik 34") == (1, 2)       # the number kept, the surname lost


def test_a_mock_run_plays_a_scenario_end_to_end(tmp_path):
    sc = evals.load_scenario(vb.SCENARIOS / "voice_cut_in_order.yaml")
    manifest = [{**i, "seconds": 3.0} for i in vc.manifest(SET, 1)]
    r = vb.play(sc, vb.MockBridge(tmp_path), manifest)
    assert [t["said"] for t in r["turns"]] == list(sc.scripted.values()) and [t["heard"] for t in r["turns"]] == list(sc.scripted.values())
    assert [t["cut_in"] for t in r["turns"]] == [False, True] and r["turns"][1]["cancelled"] is True
    assert r["turns"][0]["first_sound_s"] is not None and r["connected_s"] > 6 and r["checks"]
    m = vb.metrics([r], 0.05, 0.0)
    assert m["cut_ins"] == 1 and m["cut_ins_cancelled"] == 1 and m["wer_mean"] == 0
    assert m["voice_usd"] == round((r["connected_s"] + vb.OPEN_SECONDS) / 60 * 0.05, 4)   # the opening seconds are billed too
    garbled = vb.play(evals.load_scenario(vb.SCENARIOS / "voice_card_refused_vin.yaml"), vb.MockBridge(tmp_path / "g", garble=False), manifest)
    assert garbled["turns"][0]["wer"] == 0


def test_a_live_run_stops_before_it_spends():
    import pytest
    with pytest.raises(SystemExit):
        vb.LiveBridge()
