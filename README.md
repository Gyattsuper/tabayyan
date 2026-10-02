# تبيّن | Tabayyan

**Live demo:** https://tabayyan.onrender.com (free hosting: the first visit after a quiet period can take up to a minute to wake up)

Verify Quran and hadith quotes against authenticated sources before sharing them.

Paste a message, or select text on any page with the Chrome extension. Tabayyan finds the
verse or hadith in it, searches the Quran and nine major hadith collections, and returns one of:

- **موجود / Found**: exact reference, plus each scholar's grading for hadiths
- **مطابق جزئيًا / Partial match**: the text exists but the wording was changed; the changed words are highlighted next to the correct text
- **غير موجود / Not found**: not in the indexed sources; the user is referred to scholars

It also warns when a verse is quoted as a hadith (or the reverse), and when a hadith exists but was graded weak.
The verdict always comes from the source data, never from a language model's memory. The tool does not issue fatwas.

## How it works

```
message ──► extract quote ──► search ──► align ──► verdict + reference + highlights ──► explanation
            (Claude, with      (char n-gram   (fuzzy span,     (word-level rules)        (Claude, checked
             rule fallback)     TF-IDF)        diacritics                                  against the result)
                                               restored)
```

- `backend/arabic.py`: normalization (diacritics, hamza and alef forms, taa marbuta, honorifics)
- `backend/matcher.py`: two-stage search; "found" requires every meaningful word to match
- `backend/verify.py`: builds results, word diffs, gradings, warnings
- `backend/ai.py`: Claude API for extraction and explanations, with guards and fallback
- `backend/api.py`: FastAPI server, also serves the web app
- `frontend/`: React web app
- `extension/`: Chrome extension (right-click "تحقّق مع تبيّن", or the toolbar popup)

Sources and licenses: `SOURCES.md`. Test plan: `TESTING.md`.

## Evaluation

Compared with plain text search over the same books (1,575 generated quotes, 5 random samples),
Tabayyan finds real quotes typed with everyday spelling 99% of the time versus 8%, and catches
altered quotes with the correct text shown 99.8% of the time, while accepting none of them as
correct. Details and limits: `TESTING.md`.

## Run locally

```bash
pip install -r requirements.txt
./fetch_data.sh                      # downloads the datasets and builds the index (about 1.5 min)
python tests/run_tests.py            # 17 cases
cd frontend && npm install && npm run build && cd ..
cd backend && uvicorn api:app --port 8000
# open http://localhost:8000
```

Optional: `export ANTHROPIC_API_KEY=...` before starting the server to enable Claude extraction
and explanations. Without it, the app uses rule-based extraction and template explanations.

## Deploy (live demo)

1. Push this repo to GitHub (public).
2. On render.com: New > Blueprint > select the repo. It uses `render.yaml` and the `Dockerfile`.
3. Add `ANTHROPIC_API_KEY` in the service's environment settings.
4. The site is served at the Render URL, API included.

## Chrome extension

The extension is not on the Chrome Web Store yet (publishing it is planned). For now it is installed from this repo:

1. Download this repo (Code > Download ZIP) and unzip it.
2. Open `chrome://extensions`, turn on Developer mode, click "Load unpacked", select `extension/`.
3. Select text on any page, right-click, and choose "تحقّق مع تبيّن".

## Development history

The first commit (`440f70a`, "Starting version") was made on Sep 30, 2026, before the challenge days,
and contains the data pipeline, Arabic matcher, verdict rules and test set. Later commits show the
rest of the work. See `git log`.
