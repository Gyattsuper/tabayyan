"""Build one searchable corpus from the Quran and hadith datasets.

Sources (see SOURCES.md):
  - Quran: Tanzil "quran-simple" text for matching, King Fahd Complex
    Uthmani (Hafs) text for display. Mirrored in fawazahmed0/quran-api.
  - Hadith: fawazahmed0/hadith-api (sunnah.com data), Arabic + English,
    with gradings by named scholars.

Run once:  python build_index.py
Output:    data/corpus.json
"""
import json
from pathlib import Path

from arabic import normalize

ROOT = Path(__file__).resolve().parent.parent
Q = ROOT / "data" / "quran-api"
H = ROOT / "data" / "hadith-api"
OUT = ROOT / "data" / "corpus.json"

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
    surah_name = {c["chapter"]: c["arabicname"] for c in info["chapters"]}
    simple = load(Q / "editions" / "ara-quransimple.min.json")["quran"]
    uthmani = load(Q / "editions" / "ara-quranuthmanihaf.min.json")["quran"]
    english = load(Q / "editions" / "eng-ummmuhammad.min.json")["quran"]
    for s, u, e in zip(simple, uthmani, english):
        records.append({
            "type": "quran",
            "ref": f"{surah_name[s['chapter']]}، آية {s['verse']}",
            "surah": s["chapter"],
            "ayah": s["verse"],
            "text": u["text"],
            "english": e["text"],
            "norm": normalize(s["text"]),
        })

    # Quotes often span several short verses (e.g. Surat Al-Ikhlas), so also
    # index runs of 2 and 3 consecutive verses within the same surah.
    rows = list(zip(simple, uthmani, english))
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
                "text": " ".join(f"{u['text']} ({s['verse']})" for s, u, _ in run),
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

    OUT.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    nq = sum(r["type"] == "quran" for r in records)
    print(f"{nq} verses, {len(records) - nq} hadiths -> {OUT}")


if __name__ == "__main__":
    build()
