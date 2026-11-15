"""An unknown configuration key fails load_config with its name: a typo never loads silently."""
from __future__ import annotations

import pytest

from formguide.config import KEYS, load_config


def _load(tmp_path, text):
    p = tmp_path / "formguide.yaml"
    p.write_text(text)
    return load_config(p)


def test_a_typo_in_a_top_level_key_is_refused(tmp_path):
    with pytest.raises(ValueError) as e:
        _load(tmp_path, 'model: "anthropic:claude-haiku-5-5"\nconfrim_tools: [send_form]\n')
    assert "confrim_tools" in str(e.value) and "did you mean confirm_tools?" in str(e.value)


def test_a_typo_in_a_section_is_refused(tmp_path):
    with pytest.raises(ValueError) as e:
        _load(tmp_path, 'model: "anthropic:claude-haiku-5-5"\nmemory: {keep_turnz: 4}\nknowledge: {chunk_char: 900}\n')
    text = str(e.value)
    assert "memory.keep_turnz (did you mean memory.keep_turns?)" in text and "knowledge.chunk_char" in text


def test_every_known_key_loads(tmp_path):
    cfg = _load(tmp_path, 'model: "anthropic:claude-haiku-5-5"\nconfirm_tools: [send_form]\n'
                          "memory: {keep_turns: 3}\nknowledge: {chunk_chars: 900, chunk_overlap: 100}\n"
                          "attachments: false\nsuggestions: true\ntranscripts: memory\n")
    assert cfg.confirm_tools == ["send_form"] and cfg.memory.keep_turns == 3
    assert cfg.knowledge.store.chunk_chars == 900 and cfg.knowledge.store.chunk_overlap == 100
    assert {"confirm_tools", "knowledge", "models"} <= set(KEYS)
