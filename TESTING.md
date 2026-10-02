# Test plan

Two levels of testing:

1. `python tests/run_tests.py`: 17 hand-written cases covering each behavior (all passing).
2. `python eval/run_eval.py <seed>`: a larger generated evaluation that compares Tabayyan with plain
   text search. Results below.

## Evaluation against an alternative

**The alternative:** what a careful person can do today without Tabayyan. Remove the diacritics and
search the same nine books for the exact words, like Ctrl+F on a hadith website. Both search the same
sources, so the comparison isolates what the matching and verdict logic add.

**The test set,** generated from the sources with a fixed random seed, 5 seeds:

- *real/plain*: 60 hadith passages (from the narrated text, not the chain) and 40 verses, 9 words each, typed without diacritics
- *real/casual*: the same, typed the way people often write (أ إ آ → ا، ة → ه، ى → ي)
- *altered*: the same with one word inside the quote replaced or dropped
- *unsourced*: 15 popular sayings commonly attributed to the Prophet ﷺ that are not in these books

**Results (500 quotes per group over 5 seeds, 75 for unsourced):**

| Task | Plain text search | Tabayyan |
|---|---|---|
| Finds a real quote typed without diacritics | 88.2% | **99.2%** |
| Finds a real quote typed with everyday spelling | 7.8% | **99.2%** |
| Detects an altered quote and shows the correct text | 0% (can only say "not found") | **99.8%** |
| Accepts an altered quote as correct | 0% | **0%** |
| Reports unsourced sayings as not found | 100% | **100%** |

Raw results per item: `eval/results_seed*.json`. Summary: `eval/summary.json`.

**What the evaluation caught and how it was fixed.** The first run showed that **28% of altered
quotes were accepted as "found"**, mostly when one word was dropped or replaced by a common word
like "الله" that the coverage check ignored. The verdict was changed so that "found" requires a
word-for-word match with nothing changed or skipped inside the quote (`is_exact` in
`backend/matcher.py`). After the fix: 0 of 500. The same run showed a 3-word saying
("خير الأمور أوسطها") reported as a partial match because it shared 2 common words with a real
hadith; partial matches now need at least 3 shared meaningful words.

**Remaining misses (0.8%)** are passages from the chain of narration or from Tirmidhi's own
comments ("قال أبو عيسى..."), which users don't quote in practice. They are reported as
"partial", never as "found" for the wrong text.

**Limits of this evaluation.** The quotes are generated from the sources, not collected from real
messages, and the unsourced list is small. Testing with real users (imams, content creators) and
real forwarded messages is the next step.

## What is tested and why

| Area | Case in `tests/cases.json` | Expected | Risk it covers |
|---|---|---|---|
| Exact hadith | إنما الأعمال بالنيات... | found, Bukhari | Basic recall; cites the strongest collection first |
| Altered hadith | إنما الأعمال بالنوايا وإنما لكل إنسان... | partial | Changed words must not pass as correct |
| Valid variant wording | الأعمال بالنية ولكل امرئ ما نوى | found | Another authentic narration must not be flagged as wrong |
| No diacritics, spelling variants | لا يؤمن احدكم حتى يحب لاخيه... | found | Normalization of hamza, alef, taa marbuta |
| Popular fabrications | اطلبوا العلم ولو في الصين / النظافة من الإيمان / حب الوطن من الإيمان | not_found | Short phrases sharing filler words ("من الإيمان") with real hadiths |
| Exact verse, multi-verse | سورة الإخلاص 1-3 | found | Quotes spanning consecutive verses |
| Altered verse | ليعبدوني instead of ليعبدون | partial | A single changed word in the Quran is never accepted |
| Verse quoted as hadith | قال رسول الله ﷺ: إن الله مع الصابرين | found (Quran) + warning | Misattribution |
| Hadith quoted as verse | قال تعالى: المسلم من سلم المسلمون... | found (Bukhari) + warning | Misattribution |
| Weak hadith | اتقوا فراسة المؤمن | found + weak warning | "Found" must not read as "authentic" |
| Long message | WhatsApp-style text with greeting and "انشروها" | found | Extraction from surrounding text |
| Unrelated text / too short | shopping sentence / الله أكبر | not_found | No false matches |
| Companion's saying | قال عمر بن الخطاب لقوم يوقدون نارا: يا أهل الضوء | not_found, "قول منسوب لغير النبي ﷺ" | A saying outside the hadith books must not be shown as a fabricated hadith |
| No Arabic text | "ar", or only "ﷺ" | a message asking for the text | No crash when there is nothing to search (found while fixing the row above) |

The last two rows were added after a user tried a saying of Umar ibn al-Khattab (رضي الله عنه).
It is not in the nine books, so the tool showed the red "not found" warning meant for hadiths,
which read as if the saying were false. Now, when a message attributes a text to a companion or a
scholar, the result says the search covers only the Quran and hadith books and does not judge the
attribution. These are checked by hand in the web app; `tests/run_tests.py` covers the matcher only.

## Safety checks on the AI parts

- **Extraction:** quotes returned by Claude are kept only if they appear in the user's message
  (after normalization). Tested with a simulated response containing an invented phrase: it was dropped.
- **Explanations:** rejected and replaced with a template if they name a book, or any number,
  that is not in the computed result. Tested with explanations citing the wrong book, a wrong
  number, and Musnad Ahmad (not indexed): all rejected.
- **API unavailable:** rule-based extraction and template explanations take over; same verdicts.

## Known limits

- "Not found" covers only the indexed collections. The interface says so every time and does not
  call the text fabricated.
- Gradings are shown as provided by the dataset, per scholar, without our own judgment. Conflicting
  gradings are labeled "مختلف في درجته" and all are shown.
- Very short quotes (under 3 words) are not judged, since they are too ambiguous.
- Sayings of companions and scholars (آثار) are only found if they appear in the nine books. Most
  are reported elsewhere, so for these the tool says it cannot judge the attribution.

## Performance

54,430 records (6,236 verses plus runs of 2 to 3 verses, and 36,064 hadiths). About 0.06 s per check,
1.3 s startup, 264 MB peak memory.
