# Test plan

Run: `python tests/run_tests.py` (17 cases, all passing).

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

## Performance

54,430 records (6,236 verses plus runs of 2 to 3 verses, and 36,064 hadiths). About 0.06 s per check,
1.3 s startup, 264 MB peak memory.
