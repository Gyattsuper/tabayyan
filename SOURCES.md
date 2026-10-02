# Sources, tools and licenses

Tabayyan only states that a text exists in, or is graded by, the sources below.
It never issues rulings and does not generate references from a language model.

## Quran

| Use | Text | Origin | Mirror used | License |
|---|---|---|---|---|
| Matching and display | Quran Simple, with diacritics (Tanzil) | tanzil.net | github.com/fawazahmed0/quran-api (`ara-quransimple`) | Tanzil terms: verbatim copies allowed with attribution, text must not be changed |
| Surah names | Standard Arabic names | (written in `backend/surahs.py`, checked against the dataset order) | | |
| English meaning, and matching English quotes | Saheeh International (Umm Muhammad) | tanzil.net | github.com/fawazahmed0/quran-api (`eng-ummmuhammad`) | Tanzil terms |
| Matching English quotes | Abdullah Yusuf Ali | tanzil.net | quran-api (`eng-abdullahyusufal`) | Tanzil terms |
| Matching English quotes | Marmaduke Pickthall | tanzil.net | quran-api (`eng-mohammedmarmadu`) | Tanzil terms |
| Matching English quotes | Hilali and Khan | tanzil.net | quran-api (`eng-muhammadtaqiudd`) | Tanzil terms |

## Hadith

Nine collections from github.com/fawazahmed0/hadith-api (data originally from sunnah.com),
Arabic and English:

صحيح البخاري، صحيح مسلم، سنن أبي داود، جامع الترمذي، سنن النسائي، سنن ابن ماجه، موطأ مالك، الأربعون النووية، الأحاديث القدسية

The English hadith translations (from the same dataset, originally sunnah.com) are used to
match English quotes and are shown next to the Arabic.

Gradings are shown per scholar as provided in the dataset (Al-Albani, Shuaib Al-Arnaut,
Zubair Ali Zai, Muhyi al-Din Abd al-Hamid, Darussalam, Ahmad Shakir). Hadiths in the
two Sahihs are labeled صحيح by virtue of the collection. Where scholars differ, all
gradings are shown rather than picking one.

## Known limits

- "Not found" means not found in the collections above. It does not by itself mean a
  text is fabricated; many texts exist in other books (e.g. Musnad Ahmad, al-Bayhaqi).
  The interface states this and refers the user to scholars.
- English quotes can only be matched to the translations listed above. A quote from another
  translation may show as a partial match; the result says this may just be a different translation.
- Sayings of companions and scholars are mostly outside these books. When a message attributes a
  text to one of them, the result says this is outside the search instead of flagging it.
- Gradings come from the dataset and have not been independently reviewed.
- Reference links go to Quran.com and Sunnah.com. For Bukhari, Abu Dawud, Tirmidhi, Nasa'i,
  Ibn Majah and Nawawi the numbering was spot-checked against Sunnah.com; Muslim and Malik use a
  different numbering there, so those link to a Sunnah.com search instead.

## Software

| Tool | Use | License |
|---|---|---|
| Python, FastAPI, Uvicorn | Backend | PSF, MIT, BSD |
| NumPy, SciPy, SQLite | Index storage | BSD, public domain |
| React, Vite | Web interface | MIT |
| Amiri, Readex Pro (Google Fonts) | Typefaces | SIL Open Font License |
| scikit-learn | Character n-gram search index | BSD-3 |
| RapidFuzz | Fuzzy alignment of quotes to sources | MIT |
| Claude API (Anthropic) | Extracting quotes from messages, explaining results | Commercial API |
| Claude (Anthropic) | AI-assisted development | Commercial |
