"""Every code example in the docs is checked against the real code (scripts/check_examples.py).

Python examples compile, import only names `formguide` has and call them with arguments that exist; formguide.yaml
examples use only keys the loader reads; browser examples import only what the widget exports and use real attributes,
plugin options and props; shell examples use real `formguide` commands and flags. An example that names something that
does not exist fails here, with its page and line.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_examples.py"


def _checker():
    spec = importlib.util.spec_from_file_location("check_examples", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_docs_example_matches_the_code(capsys):
    assert _checker().main() == 0, capsys.readouterr().out


def test_the_checks_catch_a_wrong_example():
    c = _checker()
    assert c.check_python("from formguide import FormGuide, NoSuchThing")
    assert c.check_python("from formguide import GuideConfig\nGuideConfig(langauge='de')")
    assert c.check_yaml("model: x\nconfrim_tools: [a]\n", ' title="formguide.yaml"', c.config_keys())
    exp = {e: c.exports(f) for e, f in c.ENTRIES.items()}
    assert c.check_browser("import { nope } from '@formguide/agui-chat/react-hook-form'", c.attributes(), exp)
    assert c.check_browser('<agui-chat collapse-linez="4"></agui-chat>', c.attributes(), exp)
    assert c.check_options("formguide({ getState, undoSecs: 3 })", c.members("formguide/index.ts", "FormguideOptions"), set())
    assert c.check_shell('CMD ["formguide", "serve", "--prot", "8000"]', c.cli_flags())
    assert c.check_shell("formguide serve --corz '*'", c.cli_flags())
    assert not c.check_shell('pip install "formguide[all]"', c.cli_flags())
