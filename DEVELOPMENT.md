# Development log

What was built, on which day, and why. Every step has its commits, so the history can be checked
with `git log`. Built by Mohammed Alzahrani (solo), with Claude (Anthropic) as an AI coding assistant.

**Before the challenge days.** Work started on **Sep 30, 2026**. The challenge days are **Oct 4 to 6, 2026**.
The work done before Oct 4 is listed here openly so judges can see what existed at the start.

## Sep 30: starting version

| Commit | What | Why |
|---|---|---|
| `440f70a` | Data pipeline (Quran from Tanzil, 9 hadith collections with gradings), Arabic normalization, two-stage matcher (character n-gram TF-IDF, then fuzzy alignment), verdict rules, first test cases | The core question is "is this text in the sources, and was it changed?" That has to be answered from the texts themselves, not by a language model. |
| `41be812` | FastAPI server, Claude for pulling quotes out of messages and explaining results (each with a guard and a fallback), React web app | Real messages contain greetings and "please share"; the quote has to be found first. A model may only extract text that is really in the message, and its explanation is rejected if it names a book or number not in the result. |
| `e8e7d70` | Chrome extension, Docker and Render setup, test plan, documentation | People meet these texts on social media, so checking should work without leaving the page. |

## Oct 1: measuring it

| Commit | What | Why |
|---|---|---|
| `d068c29` | Evaluation against plain text search (5 samples at the time) and a stricter "found" rule | The first run showed **28% of altered quotes were accepted as "found"**. "Found" now requires a word-for-word match inside the quote. After the fix: 0 of 500. |
| `dd84137`, `6cd2e6e` | Live demo on Render, README with results, extension pointed at the live server | So the judges can try it. |

## Oct 2: fixes from testing, English, a larger evaluation

| Commit | What | Why |
|---|---|---|
| `c6e30de` | Explanations no longer say a person graded a hadith when the grading comes from Sahih al-Bukhari or Muslim itself | Found while testing live explanations. |
| `3cca452` | Demo video script, including a message with two hadiths | Shows the Claude extraction step. |
| `ad989c2` | The site and README say the extension is a beta installed from the repo, not from the Chrome Web Store | To describe it accurately. |
| `108ed42` | Sayings attributed to companions or scholars (e.g. Umar's "يا أهل الضوء") get their own result instead of the red "not found" meant for hadiths; no crash on input with nothing to search | Found by testing with a real saying of Umar ibn al-Khattab. It is not in the hadith books, and the old result read as if it were false. |
| `309a479` | Arabic / English switch for the site and extension; English quotes checked against four Quran translations and the hadith translations; Claude Sonnet 5.5 instead of Haiku | Track 4 is about people who introduce Islam to others, who often share English translations. A stronger model handles messy messages better. |
| `a18d332` | Evaluation expanded from 5 to **100 samples** (about 60,000 quotes), varied quote lengths, more unsourced sayings counted once each, English groups, 95% confidence intervals; wider search for English quotes | 5 samples and 15 sayings were too small. The larger test found English quotes that were missed (98.5% found); after the fix 99.7%. Full results and every miss explained in `TESTING.md`. |
| `6818dc1` | Checking images and screenshots (upload, paste, or right-click an image in the extension); authentic alternatives for unsourced or weak texts; a polite reply to send back, with WhatsApp sharing; the site installable as an app with "share to Tabayyan" on Android; a Learn section (hadith of the day from an-Nawawi's Forty, short lessons on gradings and on spotting fabricated messages) | Most viral religious content is shared as images. Telling someone a text is unsourced is more useful with an authentic text to share instead and a kind way to say it. In every feature, verses and hadiths shown come from the sources, not from the model. |
| `e32b216` to (this commit) | Fixes found by testing the new features on the live site: Claude's replies were silently falling back to templates because the model can return a "thinking" block before its text; hadith links ended in ".0"; images are now accepted only if the file bytes are a real JPG, PNG, WebP or GIF. Feature tests added (`tests/run_feature_tests.py`). | Every feature was tested on the live site, and the server now logs failed AI calls so problems are visible. |

## Oct 4 to 6: challenge days

Planned:

- User testing with 3 to 5 people (an imam or teacher, content creators, people who share religious
  messages), with real forwarded messages. Results will be added to `TESTING.md` and the deck.
- Fixes based on what they find.

## Main design decisions

- **The verdict never comes from a language model.** Claude only finds the quote in the message and
  explains a result that was already computed from the sources. Both steps are checked, and the app
  works without Claude.
- **"Found" means word for word.** A single changed word in a verse or hadith is never accepted.
- **"Not found" is not "fabricated".** The tool only knows the books it searches, says so every time,
  and refers the user to scholars.
- **Gradings are shown as the scholars gave them**, all of them, without choosing between them.
