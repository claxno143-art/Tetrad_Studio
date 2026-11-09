"""Builds a lemma frequency rank for the Reader.

Two signals, both reduced to derived numbers only (no source tables are shipped):
- OpenSubtitles word forms (hermitdave FrequencyWords, CC BY-SA 4.0), lemmatized
- public-domain 19th-century literature from the RussianNovels / word2vec-russian-novels corpora

Output: data/ranks.json  {lemma: rank}, data/lemma_pos.json {lemma: POS}
"""
import collections, json, math, os, re, glob
import pymorphy3

SRC = os.environ.get('READER_SRC', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
OUT = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(OUT, exist_ok=True)
morph = pymorphy3.MorphAnalyzer()
cache = {}

def lemma(form):
    r = cache.get(form)
    if r is None:
        p = morph.parse(form)[0]
        r = cache[form] = (p.normal_form.replace('ё', 'е'), p.tag.POS, 'Name' in p.tag or 'Surn' in p.tag or 'Patr' in p.tag or 'Geox' in p.tag)
    return r

# subtitles
sub = collections.Counter()
for line in open(f'{SRC}/ru_50k.txt', encoding='utf-8'):
    w, n = line.split()
    if re.fullmatch(r'[а-яё-]+', w):
        sub[lemma(w)[0]] += int(n)
sub_total = sum(sub.values())

# literature: public-domain authors only, capped per book so no single novel dominates
PD = ('Chekhov', 'Dostoyevsk', 'Gogol', 'Pushkin', 'Tolstoi', 'Turgenev', 'Gorky_Foma', 'Gorky_Mat', 'Durova', 'Panaeva',
      'NKhvoshchinskaya', 'SKhvoshchinskaya', 'Vovchok', 'Zhukova', 'Gan_', 'Tur_', 'Sologub_MelkijBes', 'Krjukov')
files = [f for f in glob.glob(f'{SRC}/RussianNovels/corpus/*.txt') if os.path.basename(f).startswith(PD)]
files += glob.glob(f'{SRC}/word2vec-russian-novels/vector-school/*.txt')
lit = collections.Counter()
pos = {}
names = collections.Counter()
for f in files:
    text = open(f, encoding='utf-8', errors='ignore').read().lower()
    toks = re.findall(r'[а-яё]+(?:-[а-яё]+)?', text)[:250000]
    for t in toks:
        l, p, nm = lemma(t)
        lit[l] += 1
        pos.setdefault(l, p)
        if nm: names[l] += 1
lit_total = sum(lit.values())
print('books', len(files), 'lit tokens', lit_total, 'sub tokens', sub_total)

score = {}
for l in set(sub) | set(lit):
    a = sub[l] / sub_total * 1e6
    b = lit[l] / lit_total * 1e6
    if a + b < 0.05:
        continue
    score[l] = math.exp(0.35 * math.log(a + 0.01) + 0.65 * math.log(b + 0.01))
ranked = sorted(score, key=lambda l: -score[l])
ranks = {l: i + 1 for i, l in enumerate(ranked)}
json.dump(ranks, open(f'{OUT}/ranks.json', 'w'), ensure_ascii=False)
json.dump({l: pos.get(l) for l in ranked}, open(f'{OUT}/lemma_pos.json', 'w'), ensure_ascii=False)
print('lemmas ranked', len(ranks))
print('sample', [(l, ranks[l]) for l in ['дом', 'книга', 'цирюльник', 'чиновник', 'коллежский', 'шинель', 'государство', 'двигатель', 'юридический']  if l in ranks])
