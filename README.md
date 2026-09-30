# تبيّن | Tabayyan

Verify Quran and hadith quotes against authenticated sources before sharing them.

Paste a message (or select text on any page with the Chrome extension). Tabayyan finds the
verse or hadith in it, searches the Quran and nine major hadith collections, and returns one of:

- **موجود / Found**: exact reference, plus the grading of each scholar for hadiths
- **مطابق جزئيًا / Partial match**: the text exists but the wording was changed; shows the correct text
- **غير موجود / Not found**: not in the indexed sources; the user is referred to scholars

The verdict always comes from the source data, never from a language model's memory.
The tool does not issue fatwas.

## Starting version (before the challenge, documented per the rules)

Built before Oct 4, 2026, and submitted as the starting point:

- Data pipeline: Quran (Tanzil / King Fahd Complex) and 9 hadith collections with gradings, see `SOURCES.md`
- Arabic normalization (diacritics, alef/yaa/taa marbuta variants, honorifics)
- Two-stage matcher: character n-gram TF-IDF for recall, fuzzy span alignment for precision
- Word-level verdict rules (a single changed word in a verse is never accepted as "found")
- Rule-based quote extraction fallback
- Test set of 15 cases (`tests/cases.json`), all passing

Work during the challenge (Oct 4 to 6) is tracked in the git history after the `starting-version` tag.

## Run

```bash
pip install -r requirements.txt
./fetch_data.sh          # downloads datasets and builds data/corpus.json
python tests/run_tests.py
```
