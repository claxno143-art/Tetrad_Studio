# Reader build

Turns the passage files in `content/` into `app/reader-data.js`.

## Setup

```
python3 -m venv venv && venv/bin/pip install pymorphy3
mkdir src && cd src
git clone https://github.com/Badestrand/russian-dictionary      # OpenRussian CSVs
git clone https://github.com/JoannaBy/RussianNovels
git clone https://github.com/nevmenandr/word2vec-russian-novels
curl -LO https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/ru/ru_50k.txt
```

Set `READER_SRC` if you keep the sources somewhere other than `reader-build/src`.

## Commands

- `venv/bin/python freq.py` rebuilds the frequency ranks in `data/` (only needed if you change sources).
- `venv/bin/python build.py` builds `dist/reader-data.js` and prints passage, word and warning counts. Copy that file to `app/`.
- `venv/bin/python build.py prep content/FILE.txt` prints numbered sentences for literary excerpts, so you can write the English in `adds/`.
- `venv/bin/python merge.py adds/FILE.txt` merges translations from an `adds/` file into the content files.

## Passage format

Passages for this app are written as `ru: Russian sentence || English with [links]{русские слова}` lines. Literary excerpts use `src:`/`from:`/`to:` to pull text from the corpus, with the English supplied as numbered `N| ...` lines. Other keys you can use: `note: phrase | gloss | explanation`, `q: kind | question | *right | wrong...`, `sum:`, `fix: form=lemma`, `repl: a => b`.

Fix every `WARN` line before shipping. A warning usually means a link or note phrase doesn't match the Russian text.
