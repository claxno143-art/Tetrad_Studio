"""Builds reader-data.js for the CL Studio Reader.

Usage:
  build.py prep FILE      show numbered Russian sentences for passages that still need English
  build.py                build everything and print a report

Content files (content/*.txt) hold passages in blocks:

  === id: some-id
  title: ...            author: ...      level: 3+     genre: literature
  src: RussianNovels/corpus/Chekhov_Dama.txt          (literary excerpts only)
  from: first words of the excerpt
  to: last words of the excerpt
  ---
  ru: Russian sentence || English sentence        (original passages: one pair per line, blank line = new paragraph)
  N| English for Russian sentence N               (excerpts; "3-4|" covers two Russian sentences)
  note: lemma or phrase | gloss | explanation     (curated: rare sense, idiom, realia)
  fix: wordform=lemma                             (override a wrong lemma guess)
  q: kind | question | *right answer | wrong | wrong | wrong
  sum: model summary

In English text, [english words]{русское слово} links a phrase to its Russian partner.
"""
import glob, json, os, re, sys, unicodedata
import pymorphy3

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get('READER_SRC', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
morph = pymorphy3.MorphAnalyzer()
RANKS = json.load(open(f'{HERE}/data/ranks.json'))
WORD = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)*")
ABBR = {'т', 'е', 'г', 'гг', 'им', 'др', 'пр', 'см', 'ст', 'ч', 'руб', 'коп', 'стр', 'д', 'п', 'тыс', 'млн', 'млрд', 'ул', 'с', 'н', 'э'}

def e(s): return s.replace('ё', 'е').replace('Ё', 'Е')

# ---------- dictionary (OpenRussian, CC BY-SA 4.0) ----------
DICT = {}
for kind in ('nouns', 'verbs', 'adjectives', 'others'):
    import csv
    with open(f'{SRC}/russian-dictionary/{kind}.csv', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            bare = e(row['bare'].strip().lower())
            en = (row.get('translations_en') or '').strip()
            if not bare or not en or bare in DICT:
                continue
            acc = row['accented'].strip()
            acc = re.sub(r"(\w)'", lambda m: m.group(1) + '́', acc)
            parts = [p.strip() for p in re.split(r'[;,]', en) if p.strip()]
            gloss = ', '.join(parts[:3])
            gloss = re.sub(r'\s*\([^)]*$', '', gloss)  # drop a parenthesis the split cut open
            extra = {}
            if kind == 'verbs' and row.get('aspect'):
                extra['asp'] = row['aspect'][:2]
                if row.get('partner'): extra['pair'] = row['partner'].replace("'", '')
            if kind == 'nouns' and row.get('gender'):
                extra['gen'] = row['gender']
            DICT[bare] = dict(a=acc, g=gloss, k=kind[:-1] if kind != 'others' else 'other', **extra)
GLOSSES = {}  # my own glosses for words OpenRussian lacks
for f in glob.glob(f'{HERE}/content/glosses*.txt'):
    for line in open(f, encoding='utf-8'):
        if '|' in line and not line.startswith('#'):
            l, g = [x.strip() for x in line.split('|', 1)]
            GLOSSES[e(l.lower())] = g

# ---------- source texts ----------
_src_cache = {}
def source(path):
    if path not in _src_cache:
        raw = open(f'{SRC}/{path}', encoding='utf-8', errors='ignore').read().replace('\r', '')
        paras, cur = [], []
        for line in raw.split('\n'):
            if not line.strip():
                if cur: paras.append(' '.join(cur)); cur = []
                continue
            if re.match(r'\s{2,}', line) and cur:
                paras.append(' '.join(cur)); cur = []
            cur.append(line.strip())
        if cur: paras.append(' '.join(cur))
        text = '\n'.join(re.sub(r'\s+', ' ', p) for p in paras)
        text = text.replace(' -- ', ' — ').replace('--', '—').replace(' - ', ' — ')
        _src_cache[path] = text
    return _src_cache[path]

def norm_ws(s): return re.sub(r'\s+', ' ', s).strip()

def excerpt(p):
    text = source(p['src'])
    flat = text.replace('\n', '  ')  # keep paragraph marks but let anchors span them
    f, t = norm_ws(p['from']), norm_ws(p['to'])
    def find(needle, start=0):
        # match ignoring paragraph marks and whitespace differences
        pat = r'\s* ?\s*'.join(re.escape(w) for w in needle.split(' '))
        m = re.compile(pat).search(flat, start)
        return m
    a = find(f, flat.find(p['after']) if p.get('after') else 0)
    if not a: raise SystemExit(f"[{p['id']}] start anchor not found: {f}")
    b = find(t, a.start())
    if not b: raise SystemExit(f"[{p['id']}] end anchor not found: {t}")
    chunk = flat[a.start():b.end()]
    for old, new in p.get('repl', []):
        if old not in chunk: raise SystemExit(f"[{p['id']}] repl text not found: {old}")
        chunk = chunk.replace(old, new)
    parts = [norm_ws(x) for x in chunk.split(' ') if x.strip()]
    return [' '.join(parts)] if p.get('join') else parts

def split_sents(para):
    out, start = [], 0
    for m in re.finditer(r'[.!?…]+[»"”)]*\s+(?=[—–«"„(А-ЯЁA-Z0-9])', para):
        before = para[start:m.start()].split(' ')[-1].lower().strip('«"(')
        if before in ABBR or (len(before) == 1 and before.isalpha()):
            continue
        if re.match(r'[—–-]\s+[а-яё]', para[m.end():m.end() + 4]):  # «...! — сказал он»: same sentence
            continue
        out.append(para[start:m.end()].strip()); start = m.end()
    if para[start:].strip(): out.append(para[start:].strip())
    return out

# ---------- parsing content files ----------
def parse(fn):
    items, cur = [], None
    for raw in open(fn, encoding='utf-8'):
        line = raw.rstrip('\n')
        if line.startswith('==='):
            m = re.match(r'===\s*id:\s*(\S+)', line)
            cur = dict(id=m.group(1), en={}, pairs=[], notes=[], fix={}, q=[], file=os.path.basename(fn)); items.append(cur); continue
        if cur is None or line.startswith('#'):
            continue
        if line.strip() == '':
            if cur['pairs'] and cur['pairs'][-1] != None: cur['pairs'].append(None)
            continue
        if line.strip() == '---': continue
        m = re.match(r'(\d+)(?:-(\d+))?\|\s*(.*)', line)
        if m:
            cur['en'][int(m.group(1))] = (int(m.group(2) or m.group(1)), m.group(3).strip()); continue
        k, _, v = line.partition(':')
        k, v = k.strip(), v.strip()
        if k == 'ru': cur['pairs'].append(v)
        elif k == 'note': cur['notes'].append([x.strip() for x in v.split('|')])
        elif k == 'fix':
            for pair in v.split(','):
                a, b = pair.split('='); cur['fix'][e(a.strip().lower())] = e(b.strip().lower())
        elif k == 'q': cur['q'].append([x.strip() for x in v.split('|')])
        elif k == 'repl':
            for pair in v.split(' ;; '):
                a2, b2 = pair.split(' => '); cur.setdefault('repl', []).append((a2, b2))
        elif k in ('title', 'author', 'level', 'genre', 'src', 'from', 'to', 'after', 'sum', 'topic', 'source_note', 'join'):
            cur[k] = v
        else:
            raise SystemExit(f"{fn}: [{cur['id']}] can't read line: {line[:80]}")
    return items

LEX, LEXIDX = [], {}
MISSING = {}
def lemma_of(form, fix):
    low = e(form.lower())
    if low in fix: return fix[low], False
    p = morph.parse(form.lower())[0]
    name = any(t in p.tag for t in ('Name', 'Surn', 'Patr', 'Geox', 'Orgn')) and form[0].isupper()
    return e(p.normal_form), name

def lex_id(lem, name, form):
    key = lem + ('#n' if name else '')
    if key not in LEXIDX:
        d = DICT.get(lem) or ({'g': GLOSSES[lem], 'a': lem} if lem in GLOSSES else None)
        if d and lem in GLOSSES and lem in DICT: d = dict(d, g=GLOSSES[lem])
        ent = {'l': lem, 'r': RANKS.get(lem, 90000)}
        if name: ent['n'] = 1
        if d:
            ent['a'] = d['a']; ent['g'] = d['g']
            for k in ('asp', 'pair', 'gen', 'k'):
                if k in d: ent[k] = d[k]
        elif not name:
            MISSING.setdefault(lem, form)
        LEXIDX[key] = len(LEX); LEX.append(ent)
    return LEXIDX[key]

def tokenize(sent, fix):
    segs, pos, first = [], 0, True
    for m in WORD.finditer(sent):
        if m.start() > pos: segs.append(sent[pos:m.start()])
        lem, name = lemma_of(m.group(0), fix)
        # a capitalized word mid-sentence that no dictionary knows is a name (foreign names slip past the tagger)
        if not name and not first and m.group(0)[0].isupper() and lem not in DICT and lem not in GLOSSES and e(m.group(0).lower()) not in fix:
            name = True
        first = False
        segs.append([m.group(0), lex_id(lem, name, m.group(0))])
        pos = m.end()
    if pos < len(sent): segs.append(sent[pos:])
    return segs

def link_english(en, toks, pid, sidx, warn):
    """[english]{русское} -> segments; returns list of str | [english, [token indexes]]"""
    out, pos = [], 0
    words = [(i, e(t[0].lower())) for i, t in enumerate(toks) if isinstance(t, list)]
    for m in re.finditer(r'\[([^\]]+)\]\{([^}]+)\}', en):
        if m.start() > pos: out.append(en[pos:m.start()])
        target = [e(x.lower()) for x in WORD.findall(m.group(2))]
        hit = None
        for j in range(len(words) - len(target) + 1):
            if [w for _, w in words[j:j + len(target)]] == target:
                hit = [i for i, _ in words[j:j + len(target)]]; break
        if hit is None:
            warn.append(f'[{pid}] s{sidx}: "{m.group(2)}" not found in Russian sentence')
            out.append(m.group(1))
        else:
            out.append([m.group(1), hit])
        pos = m.end()
    if pos < len(en): out.append(en[pos:])
    return out

def build_passage(p, warn):
    fix = p['fix']
    if p.get('src'):
        paras = [split_sents(x) for x in excerpt(p)]
    else:
        paras, cur = [], []
        for x in p['pairs']:
            if x is None:
                if cur: paras.append(cur); cur = []
            else:
                cur.append(x)
        if cur: paras.append(cur)
    sents, layout, n = [], [], 0
    for para in paras:
        row = []
        for s in para:
            n += 1
            if p.get('src'):
                ru, en = s, None
            else:
                if '||' not in s: warn.append(f"[{p['id']}] missing || in: {s[:50]}"); ru, en = s, ''
                else: ru, en = [x.strip() for x in s.split('||', 1)]
            toks = tokenize(ru, fix)
            sents.append({'ru': toks, 'en': en}); row.append(n - 1)
        layout.append(row)
    if p.get('src'):
        # English per Russian sentence (or span)
        covered = set()
        for a in sorted(p['en']):
            b, txt = p['en'][a]
            if a < 1 or b > len(sents): warn.append(f"[{p['id']}] English line {a} is outside 1-{len(sents)}"); continue
            sents[a - 1]['en'] = txt
            if b > a: sents[a - 1]['span'] = b - a + 1
            for k in range(a, b + 1): covered.add(k)
            for k in range(a + 1, b + 1): sents[k - 1]['en'] = None
        miss = [k for k in range(1, len(sents) + 1) if k not in covered]
        if miss: warn.append(f"[{p['id']}] no English for sentences {miss[:12]}{'…' if len(miss) > 12 else ''}")
    for i, s in enumerate(sents):
        if s['en']:
            # a merged English line links into all the Russian sentences it covers
            pool = []
            for k in range(i, i + s.get('span', 1)):
                pool += [(k, j, t) for j, t in enumerate(sents[k]['ru'])]
            s['en'] = link_spans(s['en'], pool, p['id'], i + 1, warn)
    # curated notes
    notes = []
    for nt in p['notes']:
        if len(nt) < 2: warn.append(f"[{p['id']}] bad note: {nt}"); continue
        phrase, gloss, expl = nt[0], nt[1], (nt[2] if len(nt) > 2 else '')
        target = [e(x.lower()) for x in WORD.findall(phrase)]
        found = None
        for si, s in enumerate(sents):
            ws = [(j, e(t[0].lower()), t[1]) for j, t in enumerate(s['ru']) if isinstance(t, list)]
            tl = [e(morph.parse(x)[0].normal_form) for x in target]
            for j in range(len(ws) - len(target) + 1):
                seg = ws[j:j + len(target)]
                if all(w == t or LEX[lid]['l'] == l for (_, w, lid), t, l in zip(seg, target, tl)):
                    found = (si, [x for x, _, _ in seg]); break
                # single word note may name the lemma rather than the form
                if len(target) == 1 and LEX[ws[j][2]]['l'] == target[0]:
                    found = (si, [ws[j][0]]); break
            if found: break
        if not found: warn.append(f"[{p['id']}] note phrase not found: {phrase}"); continue
        kind = 'idiom' if len(target) > 1 else 'sense'
        notes.append({'s': found[0], 't': found[1], 'g': gloss, 'x': expl, 'k': kind})
    qs = []
    for q in p['q']:
        if len(q) < 4 or not any(o.startswith('*') for o in q[2:]):
            warn.append(f"[{p['id']}] bad question: {q[:2]}"); continue
        opts = [o.lstrip('*') for o in q[2:]]
        qs.append({'k': q[0], 'q': q[1], 'o': opts, 'a': [o.startswith('*') for o in q[2:]].index(True)})
    if not qs: warn.append(f"[{p['id']}] has no questions")
    if not p.get('sum'): warn.append(f"[{p['id']}] has no summary")
    return {'id': p['id'], 'title': p.get('title', ''), 'author': p.get('author', ''), 'level': p.get('level', '2'),
            'genre': p.get('genre', 'everyday'), 'topic': p.get('topic', ''), 'src': p.get('source_note', ''),
            'paras': layout, 'sents': sents, 'notes': notes, 'q': qs, 'sum': p.get('sum', '')}

def link_spans(en, pool, pid, sidx, warn):
    out, pos = [], 0
    words = [(k, j, e(t[0].lower())) for k, j, t in pool if isinstance(t, list)]
    for m in re.finditer(r'\[([^\]]+)\]\{([^}]+)\}', en):
        if m.start() > pos: out.append(en[pos:m.start()])
        target = [e(x.lower()) for x in WORD.findall(m.group(2))]
        hit = None
        for j in range(len(words) - len(target) + 1):
            if [w for _, _, w in words[j:j + len(target)]] == target:
                hit = [[k, i] for k, i, _ in words[j:j + len(target)]]; break
        if hit is None:
            warn.append(f'[{pid}] s{sidx}: "{m.group(2)}" not in the Russian')
            out.append(m.group(1))
        else:
            out.append([m.group(1), hit])
        pos = m.end()
    if pos < len(en): out.append(en[pos:])
    return out

BANDS = [(1, 1000), (1001, 2000), (2001, 3500), (3501, 5000), (5001, 7500), (7501, 10000), (10001, 14000), (14001, 20000)]

def placement():
    """Real words sampled by frequency band, plus made-up words that follow Russian patterns."""
    import random
    rnd = random.Random(7)
    pos = json.load(open(f'{HERE}/data/lemma_pos.json'))
    by_rank = sorted(((r, l) for l, r in RANKS.items()), key=lambda x: x[0])
    bands = []
    for lo, hi in BANDS:
        pool = [l for r, l in by_rank if lo <= r <= hi and l in DICT and pos.get(l) in ('NOUN', 'INFN', 'ADJF', 'ADVB')
                and 4 <= len(l) <= 13 and re.fullmatch(r'[а-я]+', l) and DICT[l]['a'].count('́') <= 1]
        rnd.shuffle(pool)
        bands.append({'lo': lo, 'hi': hi, 'w': [DICT[l]['a'] for l in pool[:40]]})
    pre = ['при', 'за', 'пере', 'вы', 'об', 'раз', 'под', 'у', 'на', 'от', 'до', 'про', 'вз', 'со']
    roots = ['гроп', 'вурх', 'тлом', 'жуб', 'плик', 'смор', 'двых', 'крап', 'бряж', 'хлуп', 'мерж', 'стыб', 'чурм', 'глоч', 'трух',
             'шмыг', 'вальк', 'скреж', 'мурл', 'плют', 'зверб', 'клуш', 'дромб', 'чепл', 'гурк', 'выж', 'тюрм', 'снаб', 'брюст', 'шлеп']
    suf = ['ить', 'ать', 'ение', 'ость', 'ник', 'ливый', 'чатый', 'ание', 'ный', 'овать', 'ельный', 'ица', 'ство', 'ок']
    fake, seen = [], set()
    voiceless = set('кпстфхцчшщ')
    while len(fake) < 70:
        p, r, s = rnd.choice(pre), rnd.choice(roots), rnd.choice(suf)
        if p in ('раз', 'вз') and r[0] in voiceless: p = p[:-1] + 'с'   # рас-/вс- before a voiceless consonant
        if p in ('об', 'от', 'под', 'вз', 'вс', 'раз', 'рас') and r[0] in 'аоуэы': continue
        if s.startswith('ч') and r[-1] in 'чшщжк': continue
        w = p + r + s
        if w in seen or w in DICT or w in RANKS or morph.word_is_known(w):
            seen.add(w); continue
        seen.add(w)
        # stress the root vowel, the way most derived words are stressed
        vi = [len(p) + i for i, c in enumerate(r) if c in 'аеиоуыэюяё']
        if not vi: continue
        i = vi[-1]
        fake.append(w[:i + 1] + '́' + w[i + 1:])
    return {'bands': bands, 'fake': fake}

def main():
    files = sorted(glob.glob(f'{HERE}/content/p_*.txt'))
    if len(sys.argv) > 2 and sys.argv[1] == 'prep':
        for p in parse(sys.argv[2]):
            if p.get('src') and not p['en']:
                print(f"=== {p['id']}")
                n = 0
                for para in excerpt(p):
                    for s in split_sents(para):
                        n += 1; print(f'{n}| {s}')
                    print()
        return
    warn, out = [], []
    ids = set()
    for fn in files:
        for p in parse(fn):
            if p['id'] in ids: warn.append(f"duplicate id {p['id']}")
            ids.add(p['id'])
            out.append(build_passage(p, warn))
    # unique lemmas = real words (not names), across the whole corpus
    used = set()
    for ps in out:
        for s in ps['sents']:
            for t in s['ru']:
                if isinstance(t, list) and not LEX[t[1]].get('n'): used.add(LEX[t[1]]['l'])
    # words no dictionary knows: use the English the passage links them to (single-word links first)
    ctx = {}
    for ps in out:
        for s in ps['sents']:
            for seg in s['en']:
                if not isinstance(seg, list): continue
                hits = seg[1]
                for k, i in hits:
                    t = ps['sents'][k]['ru'][i]
                    ent = LEX[t[1]]
                    if 'g' in ent or ent.get('n'): continue
                    score = len(hits)
                    if ent['l'] not in ctx or score < ctx[ent['l']][0]:
                        ctx[ent['l']] = (score, seg[0])
    for ent in LEX:
        if 'g' not in ent and ent['l'] in ctx:
            ent['g'] = ctx[ent['l']][1]; ent['a'] = ent.get('a', ent['l']); ent['cx'] = 1
            MISSING.pop(ent['l'], None)
    used_missing = sorted(l for l in MISSING if l in used)
    data = {'lex': LEX, 'passages': out, 'place': placement()}
    os.makedirs(f'{HERE}/dist', exist_ok=True)
    with open(f'{HERE}/dist/reader-data.js', 'w', encoding='utf-8') as f:
        f.write('window.READER_DATA=' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')
    toks = sum(1 for ps in out for s in ps['sents'] for t in s['ru'] if isinstance(t, list))
    print(f'passages {len(out)}  tokens {toks}  unique lemmas {len(used)}  glossless {len(used_missing)}')
    lv = {}
    for ps in out: lv[ps['level']] = lv.get(ps['level'], 0) + 1
    print('by level', dict(sorted(lv.items())))
    gn = {}
    for ps in out: gn[ps['genre']] = gn.get(ps['genre'], 0) + 1
    print('by genre', gn)
    json.dump(used_missing, open(f'{HERE}/data/missing.json', 'w'), ensure_ascii=False)
    for w in warn: print('WARN', w)

if __name__ == '__main__':
    main()
