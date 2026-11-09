# Tetrad Studio

Free, offline Russian study tools for Linux, Windows and Mac. One launcher opens three tools:

- **Russian Reader.** 184 leveled passages from ILR 0+ to 4+ (about A1 to C2), covering everyday life, science, mechanics, law, politics and classic literature from Pushkin, Gogol, Turgenev, Tolstoy, Dostoevsky and Chekhov. Together they use over 5,000 different Russian words. Tap any word for its meaning and it goes on your learn list. Each passage ends with a few comprehension questions, and afterwards you can read it side by side with an English translation. You can start with a short vocabulary check or pick your level, and levels can be shown in ILR, CEFR or both.
- **List Trainer.** Flashcards, quizzes and root drills, plus your own word sets. You can import sets from text, CSV, Word or Excel files. Words you tap in the Reader show up here in a "From reading" set.
- **Oral Speech Memory Tool.** Write and memorize your own answers for 12  prompt types, practice with templates and phrase decks, and run mock interviews. A worked example, with complete answers from a made-up learner, shows what finished scripts could look like.

Everything runs on your own computer, with no account and no internet connection needed.

## Download

Get the installers from the [Releases](../../releases) page.

**Windows:** run `Tetrad-Studio-Setup-x.y.z.exe`. The installer isn't signed, so SmartScreen may warn you first. Click "More info", then "Run anyway". It installs for your account only and doesn't need admin rights.

**Mac:** use the `arm64` zip on Apple Silicon (M1 and later) and the `x64` zip on Intel Macs. The app isn't signed by Apple, so install it from Terminal:

```
cd ~/Downloads
unzip -q Tetrad-Studio-x.y.z-mac-arm64.zip -d /Applications
xattr -cr "/Applications/Tetrad Studio.app"
codesign --force --deep -s - "/Applications/Tetrad Studio.app"
```

**Linux (Ubuntu/Debian):**

```
cd ~/Downloads
sudo apt install ./tetrad-studio_x.y.z_all.deb
```

## What's in this repo

| Folder | What it is |
|---|---|
| `app/` | The tools themselves. Each one is a single HTML page, shared by every platform. |
| `linux/` | The GTK/WebKit launcher and the `.deb` package layout. |
| `desktop/` | The Electron wrapper for the Windows and Mac builds. |
| `reader-build/` | The pipeline that turns the passage files in `content/` into `app/reader-data.js`. |

### Building

- **Linux .deb:** run `linux/build-deb.sh`. It needs `dpkg-deb`.
- **Windows and Mac:** run `desktop/build.sh`. It needs Node 18 or later and `makensis` for the Windows installer.
- **Reader data:** see `reader-build/README.md`.

## Credits and licenses

- Code: MIT (see `LICENSE`).
- Reader word list: adapted from the [OpenRussian](https://en.openrussian.org) dictionary and [hermitdave/FrequencyWords](https://github.com/hermitdave/FrequencyWords), both CC BY-SA 4.0. The adapted list in `app/reader-data.js` and the files in `reader-build/data/` are therefore shared under CC BY-SA 4.0 (see `LICENSE-CONTENT`).
- The literary excerpts are public domain. The other passages, every translation and every note were written for this project and are CC BY-SA 4.0.
- [JSZip](https://stuk.github.io/jszip/) (MIT) and [Electron](https://www.electronjs.org/) (MIT) are bundled.

Tetrad Studio isn't affiliated with ACTFL, the Interagency Language Roundtable or any government agency. "OPI" is used only to describe the exam the tool helps you practice for.

If it helps your Russian, you can [buy me a coffee](https://buymeacoffee.com/claxno).
