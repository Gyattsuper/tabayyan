"""Measure Tabayyan against a simple alternative: plain text search.

The alternative is what a careful person does today without Tabayyan: remove
the diacritics and search the same books for the exact words (like Ctrl+F on
a hadith website). Both tools search the same sources, so the comparison
isolates what the matching and verdict logic add.

Test set (generated reproducibly from the sources, seed fixed):
  real/plain    real verses and hadith passages, typed without diacritics
  real/casual   the same, typed the way people often write (أ إ آ -> ا, ة -> ه, ى -> ي)
  altered       one word replaced or one word dropped
  unsourced     popular sayings that are commonly attributed but are not in these books

Run:  python eval/run_eval.py      (writes eval/results.json and prints a table)
"""
import json
import random
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from arabic import normalize  # noqa: E402
from matcher import Matcher, check, content_words  # noqa: E402

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 7
N_HADITH, N_QURAN = 60, 40
WINDOW = 9

UNSOURCED = [
    "اطلبوا العلم ولو في الصين",
    "النظافة من الإيمان",
    "حب الوطن من الإيمان",
    "اختلاف أمتي رحمة",
    "الدين المعاملة",
    "من عرف نفسه فقد عرف ربه",
    "اعمل لدنياك كأنك تعيش أبدا واعمل لآخرتك كأنك تموت غدا",
    "المعدة بيت الداء والحمية رأس الدواء",
    "العلم في الصغر كالنقش على الحجر",
    "تفاءلوا بالخير تجدوه",
    "خير الأمور أوسطها",
    "الساكت عن الحق شيطان أخرس",
    "صوموا تصحوا",
    "نحن قوم لا نأكل حتى نجوع وإذا أكلنا لا نشبع",
    "من علمني حرفا صرت له عبدا",
]

_DIAC = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_HON = re.compile(r"صل[ىي] الله عليه وسلم|رض[يى] الله عنهما|رض[يى] الله عنها|رض[يى] الله عنه|عليه السلام")
_CASUAL = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي"})


def strip(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^ء-ي\s]", " ", _DIAC.sub("", t))).strip()


def build_set(db) -> list[dict]:
    rnd = random.Random(SEED)
    rows = db.execute("SELECT id, type, text FROM records WHERE ayah_end IS NULL").fetchall()
    hadith = [r for r in rows if r[1] == "hadith" and len(strip(r[2]).split()) >= 30]
    rnd.shuffle(hadith)
    rnd.shuffle(quran := [r for r in rows if r[1] == "quran" and len(strip(r[2]).split()) >= WINDOW])
    items = []
    for kind, pool, n in (("hadith", hadith, N_HADITH), ("quran", quran, N_QURAN)):
        taken = 0
        for _id, _t, text in pool:
            if taken == n:
                break
            # Quote the way people quote: honorifics dropped (people add or drop them freely,
            # and a window must not start halfway through one), and the passage must carry
            # meaning, not just "عن رسول الله قال".
            w = _HON.sub(" ", strip(text)).split()
            lo = len(w) // 2 if kind == "hadith" else 0  # hadith: the narrated text, not the chain
            starts = [i for i in range(lo, len(w) - WINDOW + 1)
                      if len(content_words(normalize(" ".join(w[i:i + WINDOW])))) >= 5]
            if not starts:
                continue
            start = rnd.choice(starts)
            q = " ".join(w[start:start + WINDOW])
            taken += 1
            items.append({"group": "real/plain", "kind": kind, "text": q, "source": _id, "expect": "found"})
            items.append({"group": "real/casual", "kind": kind, "text": q.translate(_CASUAL), "source": _id, "expect": "found"})
            ws = q.split()
            # change a word inside the quote: dropping the first or last word just gives a shorter real quote
            content = [i for i, x in enumerate(ws) if 0 < i < len(ws) - 1 and len(x) > 3] or list(range(1, len(ws) - 1))
            i = rnd.choice(content)
            if rnd.random() < 0.6:
                donor = strip(rnd.choice(rows)[2]).split()
                repl = rnd.choice([x for x in donor if len(x) > 3 and x != ws[i]] or ["الناس"])
                alt = ws[:i] + [repl] + ws[i + 1:]
            else:
                alt = ws[:i] + ws[i + 1:]
            items.append({"group": "altered", "kind": kind, "text": " ".join(alt), "source": _id, "expect": "partial"})
    for t in UNSOURCED:
        items.append({"group": "unsourced", "kind": "-", "text": t, "source": None, "expect": "not_found"})
    return items


def main():
    db = sqlite3.connect(ROOT / "data" / "corpus.db")
    corpus = [strip(t) for (t,) in db.execute("SELECT text FROM records ORDER BY id")]
    items = build_set(db)

    # An "altered" quote that happens to exist verbatim elsewhere isn't altered; drop it.
    items = [it for it in items if it["group"] != "altered" or not any(f" {strip(it['text'])} " in f" {c} " for c in corpus)]

    m = Matcher()
    for it in items:
        q = strip(it["text"])
        it["baseline"] = "found" if any(f" {q} " in f" {c} " for c in corpus) else "not_found"
        v, res, _ = check(m, it["text"])
        it["tabayyan"] = v
        it["tabayyan_ref_ok"] = bool(res) and it["source"] is not None and res[0].record["id"] == it["source"]
        it["tabayyan_ref"] = res[0].record["ref"] if res and v != "not_found" else None

    groups = ["real/plain", "real/casual", "altered", "unsourced"]
    summary = {}
    for g in groups:
        sub = [it for it in items if it["group"] == g]
        n = len(sub)
        if g.startswith("real"):
            summary[g] = {"n": n,
                          "baseline_found": sum(it["baseline"] == "found" for it in sub) / n,
                          "tabayyan_found": sum(it["tabayyan"] == "found" for it in sub) / n}
        elif g == "altered":
            summary[g] = {"n": n,
                          "baseline_shows_correct_text": 0.0,
                          "baseline_wrongly_found": sum(it["baseline"] == "found" for it in sub) / n,
                          "tabayyan_partial_with_correct_text": sum(it["tabayyan"] == "partial" for it in sub) / n,
                          "tabayyan_wrongly_found": sum(it["tabayyan"] == "found" for it in sub) / n,
                          "tabayyan_not_found": sum(it["tabayyan"] == "not_found" for it in sub) / n}
        else:
            summary[g] = {"n": n,
                          "baseline_not_found": sum(it["baseline"] == "not_found" for it in sub) / n,
                          "tabayyan_not_found": sum(it["tabayyan"] == "not_found" for it in sub) / n}

    out = {"seed": SEED, "summary": summary, "items": items}
    (ROOT / "eval" / f"results_seed{SEED}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    pct = lambda x: f"{x * 100:.0f}%"
    for g, s in summary.items():
        print(g, {k: (pct(v) if isinstance(v, float) else v) for k, v in s.items()})
    for it in items:
        bad = (it["group"].startswith("real") and it["tabayyan"] != "found") or \
              (it["group"] == "altered" and it["tabayyan"] == "found") or \
              (it["group"] == "unsourced" and it["tabayyan"] != "not_found")
        if bad:
            print("MISS", it["group"], it["kind"], it["tabayyan"], it["tabayyan_ref"], "|", it["text"])


if __name__ == "__main__":
    main()
