"""Merge translation blocks into content files: merge.py ADDFILE

ADDFILE holds blocks headed '=== add: <passage id>'; each block's lines are appended
to that passage in whichever content/p_*.txt file defines it. 'repl:' lines go into the header.
"""
import glob, re, sys

blocks, cur = {}, None
for line in open(sys.argv[1], encoding='utf-8'):
    m = re.match(r'=== add:\s*(\S+)', line)
    if m:
        cur = m.group(1); blocks[cur] = []; continue
    if cur: blocks[cur].append(line.rstrip('\n'))

for fn in glob.glob('content/p_*.txt'):
    s = open(fn, encoding='utf-8').read()
    changed = False
    for pid, lines in list(blocks.items()):
        m = re.search(r'(=== id: ' + re.escape(pid) + r'\n(?:(?!===).*\n?)*)', s)
        if not m: continue
        while lines and not lines[-1].strip(): lines.pop()
        hdr = [l for l in lines if l.startswith('repl:')]
        body = [l for l in lines if not l.startswith('repl:')]
        if body and body[0].strip() != '---': body = ['---'] + body
        blk = m.group(1).rstrip('\n')
        s = s.replace(m.group(1), blk + ('\n' + '\n'.join(hdr) if hdr else '') + '\n' + '\n'.join(body) + '\n\n', 1)
        del blocks[pid]; changed = True
    if changed: open(fn, 'w', encoding='utf-8').write(s)
print('merged; not found:', list(blocks) or 'none')
