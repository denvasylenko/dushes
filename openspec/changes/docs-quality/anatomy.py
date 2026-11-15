"""Anatomy of the docs site: sections, page kinds, examples and what each example has."""
import re, json
from pathlib import Path
from collections import Counter, defaultdict
DOCS = Path('site/src/content/docs')
FENCE = re.compile(r"^[ \t]*```(\w*)[^\n]*\n(.*?)^[ \t]*```[ \t]*$", re.M | re.S)
LIVE = {'LiveDemo':'live demo','CardGallery':'card gallery','ChatFeatures':'live chat tiles','ThemePlayground':'theme playground',
        'Playground':'playground','BlocksGallery':'blocks gallery','Specimen':'specimen','ChatOnlyDemo':'live demo','SearchSpecimen':'specimen'}
rows = []
for f in sorted(DOCS.rglob('*.md*')):
    if 'specifications' in f.parts: continue
    s = f.read_text(); rel = str(f.relative_to(DOCS))
    section = rel.split('/')[0] if '/' in rel else 'home'
    sub = rel.split('/')[1] if rel.count('/') >= 2 else ''
    fences = [(l, c) for l, c in FENCE.findall(s) if l != 'mermaid']
    langs = Counter(l or 'text' for l, _ in fences)
    live = sorted({v for k, v in LIVE.items() if re.search(r'<' + k + r'\b', s)})
    comps = sorted(set(re.findall(r'^import (\w+) from .*components/(?!ui)', s, re.M)))
    rows.append(dict(page=rel, section=section, sub=sub, examples=len(fences), langs=dict(langs),
        diagram=bool(re.search(r'```mermaid|<Arch', s)), image=bool(re.search(r'<img|!\[|<picture|shots', s)), live=live, comps=comps,
        rawfile=bool(re.search(r"\?raw'", s)), tabs='<Tabs' in s, next='## Next' in s,
        kind='reference' if section == 'reference' else ('concept' if 'how-it-works' in rel or 'open-standards' in rel else ('recipe' if 'recipes' in rel else 'guide'))))
json.dump(rows, open('/private/tmp/claude-501/-Users-vasylenkodenys-Documents-form-filler-claude/e7fac811-d4ca-44e4-a04f-56e5752bb77c/scratchpad/audit/anatomy.json', 'w'), indent=1)
n = len(rows)
print('pages', n)
bysec = defaultdict(list)
for r in rows: bysec[r['section'] + ('/' + r['sub'] if r['sub'] else '')].append(r)
for k, v in sorted(bysec.items()): print(f"  {k:<34} {len(v):>2} pages, {sum(x['examples'] for x in v):>3} code examples")
print('kinds', dict(Counter(r['kind'] for r in rows)))
tot = sum(r['examples'] for r in rows)
print('code examples in all:', tot, '; by language:', dict(sum((Counter(r['langs']) for r in rows), Counter()).most_common(9)))
withex = [r for r in rows if r['examples']]
print('pages with a code example:', len(withex), '; of them with a diagram:', sum(r['diagram'] for r in withex), '; with a picture:', sum(r['image'] for r in withex), '; with something live on the page:', sum(bool(r['live']) for r in withex), '; with an example file that was run (?raw):', sum(r['rawfile'] for r in withex))
ex_no_visual = sum(r['examples'] for r in withex if not (r['diagram'] or r['image'] or r['live']))
print('code examples on pages with no diagram, picture or live thing:', ex_no_visual, 'of', tot)
print('pages with something live:', [(r['page'], r['live']) for r in rows if r['live']])
print('guides with examples but nothing visual:', [r['page'] for r in withex if r['kind'] == 'guide' and not (r['diagram'] or r['image'] or r['live'])])
