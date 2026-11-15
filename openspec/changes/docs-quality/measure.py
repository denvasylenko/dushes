"""Measure every docs page (source .md/.mdx): what a first-time reader meets."""
import re, json, sys
from pathlib import Path
DOCS = Path('site/src/content/docs')
JARGON = ['jsx_hash','forwardedProps','interrupt','directive','AG-UI','CUSTOM','checkpointer','resume','namespace','BM25','SSE',
          'thread_id','capabilities','on_interrupt','card_id','RunAgentInput','config','skeleton','layout','plugin','transcript','hand-off','domain pack']
FENCE = re.compile(r"^[ \t]*```.*?^[ \t]*```[ \t]*$", re.M | re.S)
rows = []
for f in sorted(DOCS.rglob('*.md*')):
    if 'specifications' in f.parts: continue
    s = f.read_text()
    fm = re.match(r'---\n(.*?)\n---\n', s, re.S)
    body = s[fm.end():] if fm else s
    title = re.search(r'^title:\s*(.*)$', fm.group(1), re.M).group(1).strip('"\'') if fm else f.stem
    desc = (re.search(r'^description:\s*(.*)$', fm.group(1), re.M) or [None, ''])[1].strip('"\'') if fm else ''
    body = re.sub(r'^import .*\n', '', body, flags=re.M)
    first_code = FENCE.search(body)
    prose = FENCE.sub('', body)
    prose_txt = re.sub(r'<[^>]+>', ' ', prose)
    words = len(re.findall(r'\w+', prose_txt))
    before = len(re.findall(r'\w+', re.sub(r'<[^>]+>', ' ', FENCE.sub('', body[:first_code.start()])))) if first_code else None
    paras = [p for p in re.split(r'\n\s*\n', prose) if p.strip() and not p.lstrip().startswith(('|', '#', '<', '-', '```', 'import'))]
    longest_para = max((len(re.findall(r'\w+', p)) for p in paras), default=0)
    cells = [c.strip() for line in prose.splitlines() if line.startswith('|') for c in line.split('|')]
    longest_cell = max((len(c) for c in cells), default=0)
    opening = ' '.join(re.findall(r'\S+', prose_txt)[:120])
    jarg = sorted({j for j in JARGON if re.search(r'(?<![\w-])' + re.escape(j) + r'(?![\w-])', opening)})
    sents = [x for x in re.split(r'(?<=[.!?])\s+', re.sub(r'\s+', ' ', ' '.join(paras))) if len(x.split()) > 3]
    avg_sent = round(sum(len(x.split()) for x in sents) / len(sents), 1) if sents else 0
    rows.append(dict(page=str(f.relative_to(DOCS)), title=title, desc_words=len(desc.split()), words=words,
        codes=len(FENCE.findall(body)), words_before_code=before, diagram=bool(re.search(r'```mermaid|<Arch', body)),
        summary='<Summary' in body, mistakes=bool(re.search(r'^#+ .*(mistake|pitfall|troublesh|limits)', body, re.I | re.M)),
        see=bool(re.search(r'^#+ .*(what you see|what happens|what you get|result)', body, re.I | re.M)),
        next=bool(re.search(r'^## Next', body, re.M)), h2=len(re.findall(r'^## ', body, re.M)), tables=len(re.findall(r'^\|[ -:|]+\|$', prose, re.M)),
        longest_para=longest_para, longest_cell=longest_cell, avg_sent=avg_sent, jargon=jarg))
json.dump(rows, open(sys.argv[1], 'w'), indent=1)
n = len(rows)
print(n, 'pages;', sum(r['words'] for r in rows), 'words of prose')
print('no code example:', [r['page'] for r in rows if r['codes'] == 0])
print('no diagram:', sum(not r['diagram'] for r in rows), '/', n)
print('no mistakes/limits section:', sum(not r['mistakes'] for r in rows), '/', n)
print('no "what you see":', sum(not r['see'] for r in rows), '/', n)
print('first example after >150 words:', [(r['page'], r['words_before_code']) for r in rows if (r['words_before_code'] or 0) > 150])
print('table cell > 300 chars:', sorted([(r['longest_cell'], r['page']) for r in rows if r['longest_cell'] > 300], reverse=True)[:14])
print('paragraph > 90 words:', sorted([(r['longest_para'], r['page']) for r in rows if r['longest_para'] > 90], reverse=True)[:12])
print('3+ jargon terms in the first 120 words:', sorted([(len(r['jargon']), r['page'], r['jargon']) for r in rows if len(r['jargon']) >= 3], reverse=True)[:14])
print('longest pages:', sorted([(r['words'], r['page']) for r in rows], reverse=True)[:8])
print('shortest pages:', sorted([(r['words'], r['page']) for r in rows])[:6])
