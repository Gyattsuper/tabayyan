# Sources, tools and licenses

Tabayyan only states that a text exists in, or is graded by, the sources below.
It never issues rulings and does not generate references from a language model.

## Quran

| Use | Text | Origin | Mirror used | License |
|---|---|---|---|---|
| Matching | Quran Simple (Tanzil) | tanzil.net | github.com/fawazahmed0/quran-api (`ara-quransimple`) | Tanzil terms: verbatim copies allowed with attribution, text must not be changed |
| Display | Uthmani, Hafs (King Fahd Glorious Quran Printing Complex) | qurancomplex.gov.sa | github.com/fawazahmed0/quran-api (`ara-quranuthmanihaf`) | Free for non-commercial use with attribution |
| English meaning | Saheeh International (Umm Muhammad) | tanzil.net | github.com/fawazahmed0/quran-api (`eng-ummmuhammad`) | Tanzil terms |

## Hadith

Nine collections from github.com/fawazahmed0/hadith-api (data originally from sunnah.com),
Arabic and English:

صحيح البخاري، صحيح مسلم، سنن أبي داود، جامع الترمذي، سنن النسائي، سنن ابن ماجه، موطأ مالك، الأربعون النووية، الأحاديث القدسية

Gradings are shown per scholar as provided in the dataset (Al-Albani, Shuaib Al-Arnaut,
Zubair Ali Zai, Muhyi al-Din Abd al-Hamid, Darussalam, Ahmad Shakir). Hadiths in the
two Sahihs are labeled صحيح by virtue of the collection. Where scholars differ, all
gradings are shown rather than picking one.

## Known limits

- "Not found" means not found in the collections above. It does not by itself mean a
  text is fabricated; many texts exist in other books (e.g. Musnad Ahmad, al-Bayhaqi).
  The interface states this and refers the user to scholars.
- Gradings come from the dataset and have not been independently reviewed.

## Software

| Tool | Use | License |
|---|---|---|
| Python, FastAPI, Uvicorn | Backend | PSF, MIT, BSD |
| scikit-learn | Character n-gram search index | BSD-3 |
| RapidFuzz | Fuzzy alignment of quotes to sources | MIT |
| Claude API (Anthropic) | Extracting quotes from messages, explaining results | Commercial API |
| Claude (Anthropic) | AI-assisted development | Commercial |
