"""Check every code example in the docs against the real code.

    cd backend && uv run python ../scripts/check_examples.py [--list]

An example in a docs page is text: nothing runs it, so it can name an option that never existed. This reads every
fenced block of site/src/content/docs (specifications aside) and checks what can be checked without running a server:

  python   it compiles (top-level await allowed), and every name imported from `formguide...` exists
  yaml     it parses; a formguide.yaml example uses only keys the loader reads
  js/ts    every name imported from `@formguide/agui-chat[/entry]` is exported by that entry
  html/js  every attribute on an <agui-chat> tag is one the element observes; every option given to
           `formguide({...})` and every prop of `<AguiChat>` exists
  python   also: every keyword argument of a call to a name imported from `formguide` exists
  json     it parses (examples with "..." or comments are read leniently)
  shell    every `formguide <command> --flag` is a command and a flag the CLI has

Prints one line per wrong example and the totals; exits 1 when an example is wrong, so CI fails.
"""
from __future__ import annotations

import ast
import importlib
import inspect
import json
import re
import sys
import textwrap
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "site" / "src" / "content" / "docs"
WIDGET = ROOT / "packages" / "agui-chat" / "src"
FENCE = re.compile(r"^([ \t]*)```(\w+)([^\n]*)\n(.*?)^[ \t]*```[ \t]*$", re.M | re.S)

ENTRIES = {"": "index.ts", "/formguide": "formguide/index.ts", "/highlight": "highlight.ts", "/react": "react.ts",
           "/react-hook-form": "rhf.ts"}
HTML_GLOBAL = {"id", "class", "style", "slot", "hidden", "part", "tabindex", "dir"}


# ---------------------------------------------------------------- what the real code offers
def config_keys() -> set[str]:
    """The top-level keys load_config reads."""
    src = (ROOT / "backend" / "formguide" / "config.py").read_text(encoding="utf-8")
    body = src[src.index("def load_config"):]
    return set(re.findall(r'raw(?:\.get\(|\[)"(\w+)"', body))


def exports(file: str, seen: set[str] | None = None) -> set[str]:
    """Names a widget source file exports, following `export ... from './x'` and `export * from`."""
    seen = seen or set()
    path = (WIDGET / file)
    if not path.is_file():
        for ext in (".ts", ".tsx", "/index.ts"):
            if (WIDGET / (file + ext)).is_file():
                path = WIDGET / (file + ext)
                break
    if str(path) in seen or not path.is_file():
        return set()
    seen.add(str(path))
    src = re.sub(r"/\*.*?\*/|//[^\n]*", "", path.read_text(encoding="utf-8"), flags=re.S)
    names = set(re.findall(r"export\s+(?:declare\s+)?(?:async\s+)?(?:function\*?|const|let|class|interface|type|enum)\s+(\w+)", src))
    for inner in re.findall(r"export\s+(?:type\s+)?{([^}]*)}", src):
        for part in inner.split(","):
            part = part.strip()
            if part:
                names.add(re.split(r"\s+as\s+", part)[-1].replace("type ", "").strip())
    base = path.parent.relative_to(WIDGET)
    for target in re.findall(r"export\s+(?:type\s+)?\*\s+from\s+'([^']+)'", src):
        names |= exports(str((base / target).as_posix()).lstrip("./"), seen)
    return names


def attributes() -> set[str]:
    src = (WIDGET / "element.ts").read_text(encoding="utf-8")
    body = src[src.index("const ATTRS"):]
    body = body[:body.index("\n}\n")]
    return {a or b for a, b in re.findall(r"(?:'([\w-]+)'|\b([a-z]\w*)):\s*\[", body)} | HTML_GLOBAL


# ---------------------------------------------------------------- the checks
def check_python(code: str) -> list[str]:
    code = textwrap.dedent(code)
    try:
        tree = compile(code, "<example>", "exec", flags=ast.PyCF_ONLY_AST | ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    except SyntaxError as e:
        return [f"does not compile: {e.msg} (line {e.lineno})"]
    bad = []
    imported: dict[str, object] = {}   # name in the example -> the real object, for the keyword check
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "formguide" and not node.level:
            try:
                m = importlib.import_module(node.module)
                for a in node.names:
                    if hasattr(m, a.name) and callable(getattr(m, a.name)):
                        imported[a.asname or a.name] = getattr(m, a.name)
            except Exception:  # noqa: BLE001 - reported below
                pass
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "formguide" and not node.level:
            try:
                mod = importlib.import_module(node.module)
            except Exception as e:  # noqa: BLE001
                bad.append(f"cannot import {node.module} ({type(e).__name__})")
                continue
            for a in node.names:
                if a.name != "*" and not hasattr(mod, a.name):
                    try:
                        importlib.import_module(f"{node.module}.{a.name}")
                    except Exception:  # noqa: BLE001
                        bad.append(f"{node.module} has no `{a.name}`")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in imported:
            obj = imported[node.func.id]
            try:
                params = inspect.signature(obj).parameters
            except (TypeError, ValueError):
                continue
            if any(p.kind is p.VAR_KEYWORD for p in params.values()):
                continue
            for kw in node.keywords:
                if kw.arg and kw.arg not in params:
                    bad.append(f"{node.func.id}() has no argument `{kw.arg}`")
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] == "formguide":
                    try:
                        importlib.import_module(a.name)
                    except Exception as e:  # noqa: BLE001
                        bad.append(f"cannot import {a.name} ({type(e).__name__})")
    return bad


def check_yaml(code: str, info: str, keys: set[str]) -> list[str]:
    try:
        data = yaml.safe_load(textwrap.dedent(code))
    except yaml.YAMLError as e:
        return [f"is not valid YAML: {str(e).splitlines()[0]}"]
    if not isinstance(data, dict):
        return []
    titled = "formguide.yaml" in info or "formguide.hosted.yaml" in info
    top = {str(k) for k in data}
    if titled or (top & keys and len(top & keys) * 2 >= len(top) and "pages" not in top and "turns" not in top):
        unknown = sorted(top - keys)
        if unknown:
            return [f"formguide.yaml has no key {', '.join(unknown)}"]
    return []


IMPORT = re.compile(r"import\s+(?:type\s+)?(?:(\w+)\s*,\s*)?{([^}]*)}\s+from\s+'@formguide/agui-chat([\w/-]*)'")


def check_browser(code: str, attrs: set[str], exp: dict[str, set[str]]) -> list[str]:
    bad = []
    for _default, names, entry in IMPORT.findall(code):
        if entry not in exp:
            continue   # a build file (standalone, a language pack): not a named-export entry
        for n in names.split(","):
            n = re.split(r"\s+as\s+", n.strip())[0].replace("type ", "").strip()
            if n and n not in exp[entry]:
                bad.append(f"'@formguide/agui-chat{entry}' does not export `{n}`")
    for tag in re.findall(r"<agui-chat\b([^>]*)>", code):
        tag = re.sub(r'"[^"]*"|\'[^\']*\'|\{[^}]*\}', '""', tag)
        for a in re.findall(r"(?<![\w-])([a-z][\w-]*)(?==|\s|$)", tag):
            if a not in attrs and not a.startswith(("data-", "aria-", "on")):
                bad.append(f"<agui-chat> has no attribute `{a}`")
    return bad


def members(file: str, name: str) -> set[str]:
    """The member names of `export interface <name> { ... }` in a widget source file, at its own level."""
    src = (WIDGET / file).read_text(encoding="utf-8")
    m = re.search(rf"export interface {name}\b[^{{]*{{", src)
    if not m:
        return set()
    depth, i, body = 1, m.end(), []
    while depth and i < len(src):
        ch = src[i]
        depth += ch in "{(" and 1 or (ch in "})" and -1 or 0)
        if depth == 1:
            body.append(ch)
        i += 1
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", "".join(body), flags=re.S)
    return set(re.findall(r"(?:^|[;\n])\s*(\w+)\??\s*[:(]", text))


def object_keys(code: str, start: int) -> list[str]:
    """Top-level keys of the object literal whose `{` is at `start`."""
    depth, i, keys, cur = 0, start, [], ""
    while i < len(code):
        ch = code[i]
        if ch in "\"'`":   # skip a string
            j = code.find(ch, i + 1)
            i = (j if j > 0 else len(code)) + 1
            cur += '""'
            continue
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
            if depth == 0:
                break
        if depth == 1 and ch not in "{":
            cur += ch
            if ch == ",":
                keys.append(cur[:-1])
                cur = ""
        i += 1
    keys.append(cur)
    out = []
    for k in keys:
        k = re.sub(r"//[^\n]*", "", k).strip()
        m = re.match(r"(?:async\s+)?([A-Za-z_$][\w$]*)\s*(?::|\(|$|,)", k)
        if m and not k.startswith("..."):
            out.append(m.group(1))
    return out


def check_options(code: str, plugin: set[str], chat: set[str]) -> list[str]:
    bad = []
    for m in re.finditer(r"\bformguide\(\s*{", code):
        for k in object_keys(code, m.end() - 1):
            if k not in plugin:
                bad.append(f"formguide() has no option `{k}`")
    for tag in re.findall(r"<AguiChat\b([^>]*?)/?>", code, re.S):
        tag = re.sub(r'"[^"]*"|\'[^\']*\'', '""', tag)
        tag = re.sub(r"\{(?:[^{}]|\{[^{}]*\})*\}", "{}", tag)
        for a in re.findall(r"(?<![\w.-])([a-zA-Z][\w]*)(?==|\s|$)", tag):
            if a not in chat and not a.startswith(("data", "aria", "on")):
                bad.append(f"<AguiChat> has no prop `{a}`")
    return bad


def cli_flags() -> dict[str, set[str]]:
    """`formguide <command>` -> the flags it takes, read from the argparse calls in formguide/cli.py."""
    src = (ROOT / "backend" / "formguide" / "cli.py").read_text(encoding="utf-8")
    subs = dict(re.findall(r'^\s*(\w+) = sub\.add_parser\("(\w+)"', src, re.M))
    out: dict[str, set[str]] = {name: set() for name in subs.values()}
    for var, flag in re.findall(r'^\s*(\w+)\.add_argument\("(--[\w-]+)"', src, re.M):
        if var in subs:
            out[subs[var]].add(flag)
    return out


def check_shell(code: str, cli: dict[str, set[str]]) -> list[str]:
    bad = []
    text = code.replace("\\\n", " ")
    for line in text.splitlines():
        if re.search(r'\[\s*"formguide"', line):                 # a Dockerfile's ["formguide", "serve", "--host", ...]
            line = line.replace('"', " ").replace(",", " ")
        line = re.sub(r'"[^"]*"|\'[^\']*\'', '""', line)        # quoted values are not flags
        m = re.search(r'(?<![\w/.-])formguide"?,?\s+"?([a-z]+)\b(.*)', line)   # also a Dockerfile's ["formguide", "serve", ...]
        if not m:
            continue
        cmd, rest = m.group(1), m.group(2).split("#")[0].split("&&")[0].split("|")[0]
        if cmd not in cli:
            if re.match(r"\s*(\[|@|=)", m.group(2)) or cmd in ("is", "the", "and", "to"):
                continue   # prose, or `pip install formguide[...]`
            bad.append(f"formguide has no command `{cmd}`")
            continue
        for flag in re.findall(r"(?<![\w-])(--[a-z][\w-]*)", rest):
            if flag not in cli[cmd]:
                bad.append(f"formguide {cmd} has no flag `{flag}`")
    return bad


def check_json(code: str) -> list[str]:
    text = re.sub(r"//[^\n]*", "", code)
    if "..." in text or "…" in text or re.search(r"<\w+>", text):
        return []   # an abbreviated example
    text = textwrap.dedent(text).strip()
    for attempt in (text, "{" + text + "}", "[" + text + "]"):
        try:
            json.loads(attempt)
            return []
        except json.JSONDecodeError as e:
            err = e
    return [f"is not valid JSON: {err.msg} (line {err.lineno})"]


def main() -> int:
    keys, attrs = config_keys(), attributes()
    exp = {entry: exports(file) for entry, file in ENTRIES.items()}
    cli = cli_flags()
    plugin = members("formguide/index.ts", "FormguideOptions")
    chat = members("types.ts", "ChatOptions") | members("react.ts", "AguiChatProps") | {"ref", "key", "className", "style", "children"}
    counts: dict[str, list[int]] = {}
    wrong: list[str] = []
    for f in sorted(DOCS.rglob("*.md*")):
        if "specifications" in f.parts:
            continue
        text = f.read_text(encoding="utf-8")
        for m in FENCE.finditer(text):
            lang, info, code = m.group(2).lower(), m.group(3), m.group(4)
            line = text.count("\n", 0, m.start()) + 1
            if lang in ("python", "py"):
                kind, bad = "python", check_python(code)
            elif lang in ("yaml", "yml"):
                kind, bad = "yaml", check_yaml(code, info, keys)
            elif lang in ("js", "jsx", "ts", "tsx", "html", "vue", "astro"):
                kind, bad = "browser", check_browser(code, attrs, exp) + check_options(code, plugin, chat)
            elif lang == "json":
                kind, bad = "json", check_json(code)
            elif lang in ("bash", "sh", "shell", "dockerfile", "docker") and "formguide" in code:
                kind, bad = "shell", check_shell(code, cli)
            else:
                continue
            c = counts.setdefault(kind, [0, 0])
            c[0] += 1
            if bad:
                c[1] += 1
                wrong += [f"{f.relative_to(DOCS)}:{line} [{lang}] {b}" for b in dict.fromkeys(bad)]
    for w in wrong:
        print(w)
    total, bad_n = sum(c[0] for c in counts.values()), sum(c[1] for c in counts.values())
    print("; ".join(f"{k}: {c[0]} checked, {c[1]} wrong" for k, c in sorted(counts.items())))
    print(f"{total} examples checked, {bad_n} wrong")
    return 1 if bad_n else 0


if __name__ == "__main__":
    sys.exit(main())
