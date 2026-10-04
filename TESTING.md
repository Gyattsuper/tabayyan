# Test plan

Two levels of testing:

1. `python tests/run_tests.py`: 22 hand-written cases covering each behavior (all passing).
   `python tests/run_feature_tests.py`: 14 checks for the guards, templates, image loading and
   alternative retrieval (all passing). The AI-dependent parts were also tested on the live site.
2. `python eval/run_eval.py [n_samples]`: a large generated evaluation that compares Tabayyan with
   plain text search, in Arabic and English. Results below.

## Evaluation against an alternative

**The alternative:** what a careful person can do today without Tabayyan. Remove the diacritics and
search the same nine books for the exact words, like Ctrl+F on a hadith website. For English: search
the same translations for the exact words (ignoring capitals and punctuation). Both search the same
sources, so the comparison isolates what the matching and verdict logic add.

**The test set** is generated from the sources. Each of **100 random samples** (fixed seeds 1 to 100,
so anyone can rerun it) draws new quotes:

- *real/plain*: 60 hadith passages (from the narrated text, not the chain) and 40 verses, 6 to 15 words long, typed without diacritics
- *real/casual*: the same, typed the way people often write (أ إ آ → ا، ة → ه، ى → ي)
- *altered*: the same with one word inside the quote replaced or dropped
- *english/real*: 40 verses (Saheeh International) and 60 hadiths (sunnah.com translation, the Prophet's words), 6 to 15 words
- *english/altered*: the same with one word replaced or dropped
- *unsourced*: 49 popular sayings commonly attributed to the Prophet ﷺ that are not in these books (Arabic), and 23 in English. These are fixed lists, so each saying is counted once.

**Results.** 10,000 quotes per group (about 60,000 in total). The range after each number is the
95% confidence interval.

| Task | Plain text search | Tabayyan |
|---|---|---|
| Finds a real quote typed without diacritics | 82.3% | **99.4%** (99.2 to 99.5) |
| Finds a real quote typed with everyday spelling | 6.7% | **99.4%** (99.2 to 99.5) |
| Detects an altered quote and shows the correct text | 0% (can only say "not found") | **98.1%** (97.8 to 98.4) |
| Accepts an altered quote as correct | 0% | **0.8%** (see below) |
| Reports unsourced sayings as not found (49) | 100% | **100%** (92.7 to 100) |
| English: finds a real quote | 99.9% | **99.7%** (99.5 to 99.8) |
| English: detects an altered quote and shows the correct text | 0% | **94.0%** (93.6 to 94.5) |
| English: accepts an altered quote as correct | 0% | **0%** |
| English: reports unsourced sayings as not found (23) | 100% | **95.7%** (22 of 23) |

By type: real verses are found 100% of the time in both languages; real hadith passages 99.0%
(Arabic) and 99.4% (English).

Raw results per quote: `eval/results.json.gz`. Summary: `eval/summary.json`.

**Reading the misses honestly:**

- *Altered quotes accepted (0.8%, 83 of 9,986).* We checked all 83. In every one, the changed word
  was in the chain of narration before "قال رسول الله" or "عن النبي". Tabayyan treats the text after
  that phrase as the quote, and that part was correct. So the verdict on the quoted words was right,
  but a change in the narrator chain before them is not checked. Real messages rarely quote chains.
- *Real quotes missed (Arabic 0.6%).* Passages from the chain of narration or from Tirmidhi's own
  comments ("قال أبو عيسى..."). They are reported as "partial", never as "found" for a wrong text.
- *English altered quotes not detected (5.9%).* Reported as "not found" instead of "partial", mostly
  short quotes made of common words where the changed word left too few distinctive words to find
  the source. The quote is still not accepted as correct.
- *English unsourced (1 of 23).* "Die before you die" (4 words) was reported as a partial match to a
  hadith that shares its words. The result shows the real hadith text, so the user sees the difference.
- *English real quotes:* plain search is slightly ahead (99.9% vs 99.7%) because these quotes are exact
  copies of the translation, which is the easiest case for plain search. Tabayyan's advantage in English
  is detecting changed words and different spellings, not exact copies.

**History of this evaluation.** The first version (Oct 1) used 5 samples, quotes of exactly 9 words,
and 15 unsourced sayings counted once per sample. That was too small, so on Oct 2 it was expanded to
the version above (100 samples, varied quote lengths, 49 + 23 unsourced sayings counted once, English
groups, confidence intervals). The larger test found cases the small one did not (the 0.8% above, and
English quotes that needed a wider search, which was then fixed).

**What the evaluation caught and how it was fixed.** The first run showed that **28% of altered
quotes were accepted as "found"**, mostly when one word was dropped or replaced by a common word
like "الله" that the coverage check ignored. The verdict was changed so that "found" requires a
word-for-word match with nothing changed or skipped inside the quote (`is_exact` in
`backend/matcher.py`). The same run showed a 3-word saying ("خير الأمور أوسطها") reported as a
partial match because it shared 2 common words with a real hadith; partial matches now need at
least 3 shared meaningful words. The English run first found only 98.5% of real English quotes,
because each verse is indexed in four translations and fills the candidate list; the search now
looks at more candidates for English (99.7% after the fix).

**Limits of this evaluation.** The quotes are generated from the sources, not collected from real
messages, and the unsourced lists are small. Testing with real users (imams, content creators,
people who introduce Islam to others) and real forwarded messages is the next step.

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
- **Reading images:** the model is told to copy text exactly and never correct a misquoted verse,
  since a silent correction would hide the error. The text read from the image is always shown to
  the user before the result, so they can compare it with the image.
- **Authentic alternatives:** candidates are retrieved from the sources and filtered to verses and
  hadiths graded sahih or hasan. The model may only pick from that list (by id), and its excerpt must
  appear in the source text, otherwise the source text itself is shown. Its one-line reason is dropped
  if it names a book or a number.
- **Polite reply:** built only from the computed result; rejected (template used instead) if it names a
  book or number that is not in the result.
- **API unavailable:** rule-based extraction and template explanations take over; same verdicts.

## User testing (Oct 4, 2026)

Eight people tried the live site on real messages: four sheikhs, three students of Islamic sciences, and the friend who
organized the session. Their overall feedback was that the results were accurate and useful. They did not
report specific problems, and no detailed notes were recorded, so this round is a first impression, not a
measurement. Next round: a short list of questions per result (was the verdict right, was the reference
right, was the explanation clear), with each answer recorded.

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
