"""Build one searchable corpus from the Quran and hadith datasets.

Sources (see SOURCES.md):
  - Quran: Tanzil "quran-simple" text (with diacritics) for matching and
    display, so highlighted words line up exactly. Mirrored in
    fawazahmed0/quran-api.
  - Hadith: fawazahmed0/hadith-api (sunnah.com data), Arabic + English,
    with gradings by named scholars.

  - English: four English translations of the Quran (see SOURCES.md) and the
    sunnah.com English translation of the hadiths, so English quotes can be
    checked too.

Run once:  python build_index.py
Output:    data/corpus.db      texts, references, gradings (SQLite)
           data/tfidf.npz      Arabic search index (float32 sparse matrix)
           data/vectorizer.pkl, data/types.npy
           data/en_tfidf.npz   English search index (word level), en_vectorizer.pkl, en_types.npy
"""
import json
import os
import pickle
import sqlite3
from pathlib import Path

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer

from arabic import normalize
from english import normalize_en
from surahs import SURAH

ROOT = Path(__file__).resolve().parent.parent
Q = ROOT / "data" / "quran-api"
H = ROOT / "data" / "hadith-api"
DATA = Path(os.environ.get("TABAYYAN_DATA_OUT", ROOT / "data"))

BOOKS_EN = {
    "bukhari": "Sahih al-Bukhari",
    "muslim": "Sahih Muslim",
    "abudawud": "Sunan Abi Dawud",
    "tirmidhi": "Jami at-Tirmidhi",
    "nasai": "Sunan an-Nasai",
    "ibnmajah": "Sunan Ibn Majah",
    "malik": "Muwatta Malik",
    "nawawi": "40 Hadith Nawawi",
    "qudsi": "40 Hadith Qudsi",
}
# English Quran translations indexed for English quotes (file name -> translator)
QURAN_EN = {
    "ummmuhammad": "Saheeh International",
    "abdullahyusufal": "Yusuf Ali",
    "mohammedmarmadu": "Pickthall",
    "muhammadtaqiudd": "Hilali and Khan",
}
GRADE_EN = {"صحيح": "Sahih", "حسن": "Hasan", "ضعيف": "Daif", "موضوع": "Mawdu", "منكر": "Munkar",
            "شاذ": "Shadh", "باطل": "Batil", "مرسل": "Mursal", "مقطوع": "Maqtu", "موقوف": "Mawquf"}

BOOKS = {
    "bukhari": "صحيح البخاري",
    "muslim": "صحيح مسلم",
    "abudawud": "سنن أبي داود",
    "tirmidhi": "جامع الترمذي",
    "nasai": "سنن النسائي",
    "ibnmajah": "سنن ابن ماجه",
    "malik": "موطأ مالك",
    "nawawi": "الأربعون النووية",
    "qudsi": "الأحاديث القدسية",
}
SAHIHAYN = {"bukhari", "muslim"}

GRADE_AR = {
    "sahih": "صحيح", "hasan": "حسن", "daif": "ضعيف", "da'if": "ضعيف",
    "maudu": "موضوع", "mawdu": "موضوع", "munkar": "منكر", "shadh": "شاذ",
    "batil": "باطل", "mursal": "مرسل", "maqtu": "مقطوع", "mauquf": "موقوف", "mawquf": "موقوف",
}
SCHOLAR_AR = {
    "Al-Albani": "الألباني",
    "Shuaib Al Arnaut": "شعيب الأرناؤوط",
    "Zubair Ali Zai": "زبير علي زئي",
    "Muhammad Muhyi Al-Din Abdul Hamid": "محيي الدين عبد الحميد",
    "Darussalam": "دار السلام",
    "Ahmad Muhammad Shakir": "أحمد شاكر",
    "Bashar Awad Maarouf": "بشار عواد معروف",
    "Abu Ghuddah": "عبد الفتاح أبو غدة",
    "Muhammad Fouad Abd al-Baqi": "محمد فؤاد عبد الباقي",
    "Salim al-Hilali": "سليم الهلالي",
}


def grade_bucket(label: str) -> str:
    """Collapse detailed grades like 'Hasan Sahih' or 'Daif Isnaad' to one word."""
    l = label.lower().replace("'", "")
    for key in ("maudu", "mawdu", "batil", "munkar", "shadh", "mursal", "maqtu", "mauquf", "mawquf",
                "daif", "da'if", "sahih", "hasan"):
        if key.replace("'", "") in l:
            return GRADE_AR[key]
    return label


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build():
    records = []

    en_records = []  # (record index, translator, text)
    info = load(Q / "info.min.json")
    surah_name = SURAH  # standard names; the dataset's have inconsistent diacritics and hamzas
    surah_en = {c["chapter"]: c["name"] for c in info["chapters"]}
    simple = load(Q / "editions" / "ara-quransimple.min.json")["quran"]
    english = load(Q / "editions" / "eng-ummmuhammad.min.json")["quran"]
    translations = {name: load(Q / "editions" / f"eng-{key}.min.json")["quran"] for key, name in QURAN_EN.items()}
    for idx, (s, e) in enumerate(zip(simple, english)):
        for name, verses in translations.items():
            en_records.append((len(records), name, verses[idx]["text"]))
        records.append({
            "type": "quran",
            "ref": f"{surah_name[s['chapter']]}، آية {s['verse']}",
            "ref_en": f"Surah {surah_en[s['chapter']]} {s['chapter']}:{s['verse']}",
            "surah": s["chapter"],
            "ayah": s["verse"],
            "text": s["text"],
            "english": e["text"],
            "norm": normalize(s["text"]),
        })

    # Quotes often span several short verses (e.g. Surat Al-Ikhlas), so also
    # index runs of 2 and 3 consecutive verses within the same surah.
    rows = [(s, None, e) for s, e in zip(simple, english)]
    for size in (2, 3):
        for i in range(len(rows) - size + 1):
            run = rows[i:i + size]
            if run[0][0]["chapter"] != run[-1][0]["chapter"]:
                continue
            c = run[0][0]["chapter"]
            a, b = run[0][0]["verse"], run[-1][0]["verse"]
            for name, verses in translations.items():
                en_records.append((len(records), name, " ".join(v["text"] for v in verses[i:i + size])))
            records.append({
                "type": "quran",
                "ref": f"{surah_name[c]}، الآيات {a}-{b}",
                "ref_en": f"Surah {surah_en[c]} {c}:{a}-{b}",
                "surah": c,
                "ayah": a,
                "ayah_end": b,
                "text": " ".join(f"{s['text']} ({s['verse']})" for s, _, _ in run),
                "english": " ".join(e["text"] for _, _, e in run),
                "norm": " ".join(normalize(s["text"]) for s, _, _ in run),
            })

    for key, title in BOOKS.items():
        ara = load(H / "editions" / f"ara-{key}.min.json")["hadiths"]
        eng = {h["hadithnumber"]: h for h in load(H / "editions" / f"eng-{key}.min.json")["hadiths"]}
        for h in ara:
            text = h["text"].strip()
            if not text:
                continue
            en = eng.get(h["hadithnumber"], {})
            grades = h.get("grades") or en.get("grades") or []
            if key in SAHIHAYN:
                grades_out = [{"scholar": title, "grade": "صحيح", "scholar_en": BOOKS_EN[key], "grade_en": "Sahih"}]
            else:
                grades_out = []
                for g in grades:
                    if g.get("grade", "").strip() in ("", "-"):
                        continue
                    ar = grade_bucket(g["grade"])
                    grades_out.append({"scholar": SCHOLAR_AR.get(g["name"], g["name"]), "grade": ar,
                                       "scholar_en": g["name"], "grade_en": GRADE_EN.get(ar, g["grade"])})
            num = f"{h['hadithnumber']:g}" if isinstance(h["hadithnumber"], float) else f"{h['hadithnumber']}"
            if en.get("text", "").strip():
                en_records.append((len(records), "sunnah.com", en["text"]))
            records.append({
                "type": "hadith",
                "ref": f"{title}، رقم {num}",
                "ref_en": f"{BOOKS_EN[key]} {num}",
                "book": key,
                "number": h["hadithnumber"],
                "text": text,
                "english": en.get("text", ""),
                "grades": grades_out,
                "norm": normalize(text),
            })

    write(records, en_records)
    nq = sum(r["type"] == "quran" for r in records)
    print(f"{nq} verse records, {len(records) - nq} hadiths, {len(en_records)} English texts -> {DATA}")


def write(records, en_records):
    DATA.mkdir(parents=True, exist_ok=True)
    db_path = DATA / "corpus.db"
    db_path.unlink(missing_ok=True)
    db = sqlite3.connect(db_path)
    db.execute("""CREATE TABLE records (id INTEGER PRIMARY KEY, type TEXT, ref TEXT, book TEXT,
                  number REAL, surah INTEGER, ayah INTEGER, ayah_end INTEGER,
                  text TEXT, english TEXT, grades TEXT, norm TEXT, ref_en TEXT)""")
    db.executemany(
        "INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(i, r["type"], r["ref"], r.get("book"), r.get("number"), r.get("surah"), r.get("ayah"),
          r.get("ayah_end"), r["text"], r.get("english", ""), json.dumps(r.get("grades", []), ensure_ascii=False),
          r["norm"], r["ref_en"]) for i, r in enumerate(records)])
    db.execute("""CREATE TABLE en_records (id INTEGER PRIMARY KEY, record_id INTEGER, translator TEXT,
                  en_text TEXT, en_norm TEXT)""")
    en_norms = [normalize_en(t) for _, _, t in en_records]
    db.executemany("INSERT INTO en_records VALUES (?,?,?,?,?)",
                   [(i, rid, name, t, n) for i, ((rid, name, t), n) in enumerate(zip(en_records, en_norms))])
    db.commit()
    db.close()

    # English: word-level index (character n-grams over long English texts would not fit in memory).
    en_vec = TfidfVectorizer(analyzer="word", ngram_range=(1, 1), sublinear_tf=True, min_df=2,
                             token_pattern=r"[a-z0-9]+", dtype=np.float32)
    en_matrix = en_vec.fit_transform(en_norms).astype(np.float32)
    en_vec.stop_words_ = None
    sparse.save_npz(DATA / "en_tfidf.npz", en_matrix)
    with open(DATA / "en_vectorizer.pkl", "wb") as f:
        pickle.dump(en_vec, f)
    np.save(DATA / "en_types.npy", np.array([0 if records[rid]["type"] == "quran" else 1 for rid, _, _ in en_records],
                                            dtype=np.int8))

    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 4), sublinear_tf=True, min_df=2, dtype=np.float32)
    matrix = vec.fit_transform([r["norm"] for r in records]).astype(np.float32)
    vec.stop_words_ = None  # large and not needed at query time
    sparse.save_npz(DATA / "tfidf.npz", matrix)
    with open(DATA / "vectorizer.pkl", "wb") as f:
        pickle.dump(vec, f)
    np.save(DATA / "types.npy", np.array([0 if r["type"] == "quran" else 1 for r in records], dtype=np.int8))


if __name__ == "__main__":
    build()
