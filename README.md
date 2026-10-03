# تبيّن | Tabayyan

**Live demo:** https://tabayyan.onrender.com (free hosting: the first visit after a quiet period can take up to a minute to wake up)

Verify Quran and hadith quotes against authenticated sources before sharing them.

Paste a message, or select text on any page with the Chrome extension. Tabayyan finds the
verse or hadith in it, searches the Quran and nine major hadith collections, and returns one of:

- **موجود / Found**: exact reference, plus each scholar's grading for hadiths
- **مطابق جزئيًا / Partial match**: the text exists but the wording was changed; the changed words are highlighted next to the correct text
- **غير موجود / Not found**: not in the indexed sources; the user is referred to scholars

It also warns when a verse is quoted as a hadith (or the reverse), when a hadith exists but was graded weak,
and when a saying is attributed to a companion or scholar (outside what it searches, so it does not judge it).
The verdict always comes from the source data, never from a language model's memory. The tool does not issue fatwas.

**Arabic and English.** The interface and results can be switched between Arabic and English. Quotes can be
in either language: English quotes are compared with four well-known English translations of the Quran
(Saheeh International, Yusuf Ali, Pickthall, Hilali and Khan) and the sunnah.com hadith translations. A
partial match in English may just be a different translation, and the result says so.

**More than a checker:**

- **Images:** upload, paste or drop a screenshot, or right-click an image with the extension. Claude reads the
  text exactly as written (without correcting it), the text is shown to you, then checked like any message.
- **Authentic alternatives:** for a text that is not found or graded weak, Tabayyan suggests authentic hadiths
  or verses with a close meaning. They are retrieved from the sources; Claude only chooses among them and must
  quote them exactly.
- **A polite reply:** one tap drafts a kind correction you can send back to the group, with the source link,
  and a WhatsApp button.
- **Share from WhatsApp:** the site can be installed as an app on Android; then share any message to Tabayyan.
- **Learn:** a hadith of the day from an-Nawawi's Forty, and short lessons on hadith gradings and on how to
  spot a fabricated forwarded message.
- **Search the sources:** type a topic (parents, patience, neighbors) and get authentic verses and hadiths about
  it. With the AI service, Claude rewrites the topic into search phrases and drops results that only share a word with it; every result is from the sources.
- **Popular unsourced sayings:** a list of sayings that spread as hadiths but are not in the nine books; tap one
  to see the check.
- **Share as image:** any result can be saved or shared as a square card for WhatsApp status or social media.
- **Your history:** recent checks, kept only on your device.

## How it works

```
message ──► extract quote ──► search ──► align ──► verdict + reference + highlights ──► explanation
            (Claude, with      (char n-gram   (fuzzy span,     (word-level rules)        (Claude, checked
             rule fallback)     TF-IDF)        diacritics                                  against the result)
                                               restored)
```

- `backend/arabic.py`: normalization (diacritics, hamza and alef forms, taa marbuta, honorifics)
- `backend/english.py`: English normalization (punctuation, honorifics, translator insertions in brackets)
- `backend/matcher.py`: two-stage search (Arabic text, or English translations); "found" requires every meaningful word to match
- `backend/verify.py`: builds results in Arabic or English, word diffs, gradings, warnings
- `backend/ai.py`: Claude API for extraction and explanations, with guards and fallback
- `backend/extras.py`: images, authentic alternatives, polite replies, hadith of the day
- `backend/api.py`: FastAPI server, also serves the web app
- `frontend/`: React web app
- `extension/`: Chrome extension (right-click "تحقّق مع تبيّن", or the toolbar popup), Arabic or English

Sources and licenses: `SOURCES.md`. Test plan and evaluation: `TESTING.md`. What was done on which day: `DEVELOPMENT.md`.

## Evaluation

Compared with plain text search over the same books, on about 60,000 generated quotes (100 random
samples, 10,000 quotes per group, Arabic and English):

- Finds real quotes typed with everyday spelling **99.4%** of the time, versus 6.7% for plain search.
- Catches altered quotes and shows the correct text **98.1%** of the time (English: 94.0%).
  Plain search can only say "not found".
- Reports all 49 popular unsourced Arabic sayings as not found (22 of 23 in English).

Every number has a 95% confidence interval, and every miss is explained, in `TESTING.md`.

## Run locally

```bash
pip install -r requirements.txt
./fetch_data.sh                      # downloads the datasets and builds the index (about 1.5 min)
python tests/run_tests.py            # 22 cases
python tests/run_feature_tests.py    # 14 checks for images, alternatives, replies
cd frontend && npm install && npm run build && cd ..
cd backend && uvicorn api:app --port 8000
# open http://localhost:8000
```

Optional: `export ANTHROPIC_API_KEY=...` before starting the server to enable Claude extraction
and explanations. Without it, the app uses rule-based extraction and template explanations.
The model is Claude Sonnet 5.5 by default (`TABAYYAN_MODEL` to change it).

## Deploy (live demo)

1. Push this repo to GitHub (public).
2. On render.com: New > Blueprint > select the repo. It uses `render.yaml` and the `Dockerfile`.
3. Add `ANTHROPIC_API_KEY` in the service's environment settings.
4. The site is served at the Render URL, API included.

## Chrome extension

The extension is not on the Chrome Web Store yet (publishing it is planned). For now it is installed from this repo:

1. Download this repo (Code > Download ZIP) and unzip it.
2. Open `chrome://extensions`, turn on Developer mode, click "Load unpacked", select `extension/`.
3. Select text on any page, right-click, and choose "تحقّق مع تبيّن". Or right-click an image and choose
   "تحقّق من الصورة مع تبيّن".

## Development history

Work started on Sep 30, 2026, before the challenge days (Oct 4 to 6). `DEVELOPMENT.md` lists what was
done on which day, with the commits for each step. The first commit (`440f70a`, "Starting version")
contains the data pipeline, Arabic matcher, verdict rules and test set.
