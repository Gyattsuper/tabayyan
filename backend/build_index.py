"""Build one searchable corpus from the Quran and hadith datasets.

Sources (see SOURCES.md):
  - Quran: Tanzil "quran-simple" text (with diacritics) for matching and
    display, so highlighted words line up exactly. Mirrored in
    fawazahmed0/quran-api.
  - Hadith: fawazahmed0/hadith-api (sunnah.com data), Arabic + English,
    with gradings by named scholars.

Run once:  python build_index.py
Output:    data/corpus.db      texts, references, gradings (SQLite)
           data/tfidf.npz      search index (float32 sparse matrix)
           data/vectorizer.pkl, data/types.npy
"""
import json
import pickle
import sqlite3
from pathlib import Path

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer

from arabic import normalize
from surahs import SURAH

ROOT = Path(__file__).resolve().parent.parent
Q = ROOT / "data" / "quran-api"
H = ROOT / "data" / "hadith-api"
DATA = ROOT / "data"

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

    info = load(Q / "info.min.json")
    surah_name = SURAH  # standard names; the dataset's have inconsistent diacritics and hamzas
    simple = load(Q / "editions" / "ara-quransimple.min.json")["quran"]
    english = load(Q / "editions" / "eng-ummmuhammad.min.json")["quran"]
    for s, e in zip(simple, english):
        records.append({
            "type": "quran",
            "ref": f"{surah_name[s['chapter']]}، آية {s['verse']}",
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
            records.append({
                "type": "quran",
                "ref": f"{surah_name[c]}، الآيات {a}-{b}",
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
                grades_out = [{"scholar": title, "grade": "صحيح"}]
            else:
                grades_out = [
                    {"scholar": SCHOLAR_AR.get(g["name"], g["name"]), "grade": grade_bucket(g["grade"])}
                    for g in grades
                    if g.get("grade", "").strip() not in ("", "-")
                ]
            records.append({
                "type": "hadith",
                "ref": f"{title}، رقم {h['hadithnumber']:g}" if isinstance(h["hadithnumber"], float) else f"{title}، رقم {h['hadithnumber']}",
                "book": key,
                "number": h["hadithnumber"],
                "text": text,
                "english": en.get("text", ""),
                "grades": grades_out,
                "norm": normalize(text),
            })

    write(records)
    nq = sum(r["type"] == "quran" for r in records)
    print(f"{nq} verse records, {len(records) - nq} hadiths -> {DATA}")


def write(records):
    db_path = DATA / "corpus.db"
    db_path.unlink(missing_ok=True)
    db = sqlite3.connect(db_path)
    db.execute("""CREATE TABLE records (id INTEGER PRIMARY KEY, type TEXT, ref TEXT, book TEXT,
                  number REAL, surah INTEGER, ayah INTEGER, ayah_end INTEGER,
                  text TEXT, english TEXT, grades TEXT, norm TEXT)""")
    db.executemany(
        "INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [(i, r["type"], r["ref"], r.get("book"), r.get("number"), r.get("surah"), r.get("ayah"),
          r.get("ayah_end"), r["text"], r.get("english", ""), json.dumps(r.get("grades", []), ensure_ascii=False),
          r["norm"]) for i, r in enumerate(records)])
    db.commit()
    db.close()

    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 4), sublinear_tf=True, min_df=2, dtype=np.float32)
    matrix = vec.fit_transform([r["norm"] for r in records]).astype(np.float32)
    vec.stop_words_ = None  # large and not needed at query time
    sparse.save_npz(DATA / "tfidf.npz", matrix)
    with open(DATA / "vectorizer.pkl", "wb") as f:
        pickle.dump(vec, f)
    np.save(DATA / "types.npy", np.array([0 if r["type"] == "quran" else 1 for r in records], dtype=np.int8))


if __name__ == "__main__":
    build()
