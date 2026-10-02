"""Measure Tabayyan against a simple alternative: plain text search.

The alternative is what a careful person does today without Tabayyan: remove
the diacritics and search the same books for the exact words (like Ctrl+F on
a hadith website). Both tools search the same sources, so the comparison
isolates what the matching and verdict logic add.

Test set (generated reproducibly from the sources, one random sample per seed):
  real/plain    real verses and hadith passages (6 to 15 words), typed without diacritics
  real/casual   the same, typed the way people often write (أ إ آ -> ا, ة -> ه, ى -> ي)
  altered       one word replaced or one word dropped
  unsourced     popular sayings commonly attributed to the Prophet ﷺ that are not in these
                books (a fixed list, counted once, not once per seed)

  english/real      passages of the English translations (Saheeh International for verses,
                    sunnah.com for hadiths), 6 to 15 words
  english/altered   the same with one word replaced or dropped
  english/unsourced popular English sayings attributed to the Prophet ﷺ that are not in these books

Each seed draws 100 new Arabic quotes (60 hadith, 40 verses) and 100 English ones. Rates are reported with 95%
Wilson confidence intervals.

Run:  python eval/run_eval.py [n_seeds]   (default 100; writes eval/results.json.gz and eval/summary.json)
"""
import gzip
import json
import os
import random
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from arabic import normalize  # noqa: E402
from english import STOPWORDS_EN, normalize_en  # noqa: E402
from matcher import Matcher, check, content_words  # noqa: E402

N_SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 100
N_HADITH, N_QURAN = 60, 40
MIN_WORDS, MAX_WORDS = 6, 15

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
    # Added later to make this group larger. Checked by hand that none is in the nine books;
    # sayings that partly overlap a real hadith's wording were left out as ambiguous.
    "اطلب العلم من المهد إلى اللحد",
    "من تعلم لغة قوم أمن مكرهم",
    "علموا أولادكم السباحة والرماية وركوب الخيل",
    "كما تكونوا يولى عليكم",
    "النظر إلى وجه العالم عبادة",
    "حب الدنيا رأس كل خطيئة",
    "الفتنة نائمة لعن الله من أيقظها",
    "أدبني ربي فأحسن تأديبي",
    "عليكم بدين العجائز",
    "كنت كنزا مخفيا فأحببت أن أعرف",
    "لولاك لما خلقت الأفلاك",
    "توسلوا بجاهي فإن جاهي عند الله عظيم",
    "رجعنا من الجهاد الأصغر إلى الجهاد الأكبر",
    "أصحابي كالنجوم بأيهم اقتديتم اهتديتم",
    "ساعة لقلبك وساعة لربك",
    "زر غبا تزدد حبا",
    "أول ما خلق الله العقل",
    "من أخلص لله أربعين صباحا ظهرت ينابيع الحكمة من قلبه على لسانه",
    "خير الأسماء ما حمد وعبد",
    "الخلق كلهم عيال الله",
    "شاوروهن وخالفوهن",
    "نية المؤمن خير من عمله",
    "سيد القوم خادمهم",
    "حسنات الأبرار سيئات المقربين",
    "الدنيا مزرعة الآخرة",
    "لا تكرهوا البنات فإنهن المؤنسات الغاليات",
    "الناس نيام فإذا ماتوا انتبهوا",
    "موتوا قبل أن تموتوا",
    "تخلقوا بأخلاق الله",
    "ما وسعني أرضي ولا سمائي ووسعني قلب عبدي المؤمن",
    "الكاد على عياله كالمجاهد في سبيل الله",
    "إن الله يحب العبد المحترف",
    "عليكم بالعدس فإنه مبارك",
    "من بلغ الأربعين ولم يغلب خيره شره فليتجهز إلى النار",
]

UNSOURCED_EN = [
    "Seek knowledge even if you have to go to China",
    "Love of one's country is part of faith",
    "The differences among my community are a mercy",
    "Work for your worldly life as if you will live forever, and work for your hereafter as if you will die tomorrow",
    "Whoever knows himself knows his Lord",
    "Seek knowledge from the cradle to the grave",
    "Whoever learns the language of a people is safe from their plotting",
    "Fast and you will be healthy",
    "Be optimistic about good and you will find it",
    "The ink of the scholar is holier than the blood of the martyr",
    "Teach your children swimming, archery and horse riding",
    "The stomach is the house of disease and diet is the head of every cure",
    "We are a people who do not eat until we are hungry, and when we eat we do not eat our fill",
    "The world is the farm of the Hereafter",
    "We have returned from the lesser jihad to the greater jihad",
    "My companions are like the stars, whichever of them you follow you will be guided",
    "All creatures are the dependents of Allah",
    "Religion is how you treat people",
    "Marry and do not divorce, for divorce shakes the Throne of Allah",
    "The love of this world is the root of every sin",
    "Whoever is silent about the truth is a mute devil",
    "Die before you die",
    "An hour of reflection is better than a year of worship",
]

_DIAC = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_HON = re.compile(r"صل[ىي] الله عليه وسلم|رض[يى] الله عنهما|رض[يى] الله عنها|رض[يى] الله عنه|عليه السلام")
_CASUAL = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي"})


def strip(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^ء-ي\s]", " ", _DIAC.sub("", t))).strip()


def build_set(db, seed: int) -> list[dict]:
    rnd = random.Random(seed)
    rows = db.execute("SELECT id, type, text FROM records WHERE ayah_end IS NULL").fetchall()
    hadith = [r for r in rows if r[1] == "hadith" and len(strip(r[2]).split()) >= 30]
    rnd.shuffle(hadith)
    rnd.shuffle(quran := [r for r in rows if r[1] == "quran" and len(strip(r[2]).split()) >= MIN_WORDS])
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
            size = min(rnd.randint(MIN_WORDS, MAX_WORDS), len(w) - lo)
            starts = [i for i in range(lo, len(w) - size + 1)
                      if len(content_words(normalize(" ".join(w[i:i + size])))) >= min(5, size - 1)]
            if not starts:
                continue
            start = rnd.choice(starts)
            q = " ".join(w[start:start + size])
            taken += 1
            base = {"seed": seed, "kind": kind, "source": _id, "words": size}
            items.append({**base, "group": "real/plain", "text": q, "expect": "found"})
            items.append({**base, "group": "real/casual", "text": q.translate(_CASUAL), "expect": "found"})
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
            items.append({**base, "group": "altered", "text": " ".join(alt), "expect": "partial"})
    return items


def build_set_en(db, seed: int, n: int = 100) -> list[dict]:
    """English: windows of the translations people usually quote (Saheeh International for
    verses, sunnah.com for hadiths), with one word changed or dropped for the altered group."""
    rnd = random.Random(1000 + seed)
    rows = db.execute("SELECT e.id, e.record_id, r.type, e.en_text FROM en_records e JOIN records r ON r.id = e.record_id "
                      "WHERE r.ayah_end IS NULL AND e.translator IN ('Saheeh International', 'sunnah.com')").fetchall()
    rnd.shuffle(rows)
    words_pool = [w for _, _, _, t in rows[:3000] for w in normalize_en(t).split() if len(w) > 3]
    items, taken = [], 0
    n_quran = n * 2 // 5
    counts = {"quran": 0, "hadith": 0}
    for _id, rid, kind, text in rows:
        if taken == n:
            break
        if counts[kind] >= (n_quran if kind == "quran" else n - n_quran):
            continue
        # quote what people quote: words outside translator insertions, and for hadiths the
        # Prophet's words (after the first quotation mark), not "Narrated X:"
        if kind == "hadith":
            qpos = max(text.find('"'), text.find("“"))
            if qpos < 0:
                continue
            text = text[qpos + 1:]
        w = normalize_en(text).split()
        size = min(rnd.randint(MIN_WORDS, MAX_WORDS), len(w))
        if size < MIN_WORDS:
            continue
        starts = [i for i in range(0, len(w) - size + 1)
                  if len([x for x in w[i:i + size] if x not in STOPWORDS_EN]) >= min(4, size - 2)]
        if not starts:
            continue
        start = rnd.choice(starts)
        ws = w[start:start + size]
        taken += 1
        counts[kind] += 1
        base = {"seed": seed, "kind": kind, "source": rid, "words": size}
        items.append({**base, "group": "english/real", "text": " ".join(ws), "expect": "found"})
        content = [i for i, x in enumerate(ws) if 0 < i < len(ws) - 1 and x not in STOPWORDS_EN] or list(range(1, len(ws) - 1))
        i = rnd.choice(content)
        if rnd.random() < 0.6:
            repl = rnd.choice([x for x in words_pool if x != ws[i]])
            alt = ws[:i] + [repl] + ws[i + 1:]
        else:
            alt = ws[:i] + ws[i + 1:]
        items.append({**base, "group": "english/altered", "text": " ".join(alt), "expect": "partial"})
    return items


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    """95% confidence interval for a rate k/n."""
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def rate(sub, cond) -> dict:
    k = sum(1 for it in sub if cond(it))
    return {"rate": round(k / len(sub), 4) if sub else 0.0, "ci95": wilson(k, len(sub))}


_M = None


def _init():
    global _M
    _M = Matcher()


def _run(text):
    v, res, _ = check(_M, text)
    ref = res[0].record["ref"] if res and v != "not_found" else None
    return v, (res[0].record["id"] if res else None), ref


def main():
    db = sqlite3.connect(ROOT / "data" / "corpus.db")
    # One big string per form, so "is this exact text anywhere" is a single fast substring search.
    corpus = "\x00".join(f" {strip(t)} " for (t,) in db.execute("SELECT text FROM records ORDER BY id"))
    corpus_norm = "\x00".join(f" {n} " for (n,) in db.execute("SELECT norm FROM records ORDER BY id"))
    # English baseline: lowercase, punctuation removed, exact phrase search in the same translations
    corpus_en = "\x00".join(f" {normalize_en(t)} " for (t,) in db.execute("SELECT en_text FROM en_records ORDER BY id"))
    items = []
    for seed in range(1, N_SEEDS + 1):
        items += build_set(db, seed)
        items += build_set_en(db, seed)
    items += [{"seed": None, "group": "unsourced", "kind": "-", "text": t, "source": None, "expect": "not_found"}
              for t in UNSOURCED]
    items += [{"seed": None, "group": "english/unsourced", "kind": "-", "text": t, "source": None, "expect": "not_found"}
              for t in UNSOURCED_EN]

    # An "altered" quote that happens to exist elsewhere (even after normalization) isn't altered; drop it.
    items = [it for it in items if it["group"] != "altered" or
             (f" {strip(it['text'])} " not in corpus and f" {normalize(it['text'])} " not in corpus_norm)]
    items = [it for it in items if it["group"] != "english/altered" or f" {normalize_en(it['text'])} " not in corpus_en]

    for it in items:
        if it["group"].startswith("english"):
            it["baseline"] = "found" if f" {normalize_en(it['text'])} " in corpus_en else "not_found"
        else:
            it["baseline"] = "found" if f" {strip(it['text'])} " in corpus else "not_found"
    from multiprocessing import Pool
    with Pool(os.cpu_count() or 1, initializer=_init) as pool:
        outs = pool.map(_run, [it["text"] for it in items], chunksize=200)
    for it, (v, rid, ref) in zip(items, outs):
        it["tabayyan"] = v
        it["tabayyan_ref_ok"] = it["source"] is not None and rid == it["source"]
        it["tabayyan_ref"] = ref

    summary = {}
    for g in ["real/plain", "real/casual", "altered", "unsourced", "english/real", "english/altered", "english/unsourced"]:
        sub = [it for it in items if it["group"] == g]
        s = {"n": len(sub)}
        if g.startswith("real") or g == "english/real":
            s["baseline_found"] = rate(sub, lambda it: it["baseline"] == "found")
            s["tabayyan_found"] = rate(sub, lambda it: it["tabayyan"] == "found")
            s["tabayyan_found_by_kind"] = {k: rate([it for it in sub if it["kind"] == k], lambda it: it["tabayyan"] == "found")
                                           for k in ("hadith", "quran")}
        elif g.endswith("altered"):
            s["baseline_wrongly_found"] = rate(sub, lambda it: it["baseline"] == "found")
            s["tabayyan_partial_with_correct_text"] = rate(sub, lambda it: it["tabayyan"] == "partial")
            s["tabayyan_wrongly_found"] = rate(sub, lambda it: it["tabayyan"] == "found")
            s["tabayyan_not_found"] = rate(sub, lambda it: it["tabayyan"] == "not_found")
        else:
            s["baseline_not_found"] = rate(sub, lambda it: it["baseline"] == "not_found")
            s["tabayyan_not_found"] = rate(sub, lambda it: it["tabayyan"] == "not_found")
        summary[g] = s

    meta = {"seeds": N_SEEDS, "quotes_per_seed": {"arabic": N_HADITH + N_QURAN, "english": 100},
            "quote_words": [MIN_WORDS, MAX_WORDS],
            "unsourced_sayings": {"arabic": len(UNSOURCED), "english": len(UNSOURCED_EN)}}
    (ROOT / "eval" / "summary.json").write_text(json.dumps({**meta, "summary": summary}, ensure_ascii=False, indent=1),
                                                encoding="utf-8")
    with gzip.open(ROOT / "eval" / "results.json.gz", "wt", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)

    pct = lambda r: f"{r['rate'] * 100:.1f}% [{r['ci95'][0] * 100:.1f}-{r['ci95'][1] * 100:.1f}]"
    for g, s in summary.items():
        print(g, "n =", s["n"])
        for k, v in s.items():
            if isinstance(v, dict) and "rate" in v:
                print("   ", k, pct(v))
    for it in items:
        bad = (it["group"] in ("real/plain", "real/casual", "english/real") and it["tabayyan"] != "found") or \
              (it["group"].endswith("altered") and it["tabayyan"] == "found") or \
              (it["group"].endswith("unsourced") and it["tabayyan"] != "not_found")
        if bad:
            print("MISS", it["group"], it["kind"], it["tabayyan"], it["tabayyan_ref"], "|", it["text"])


if __name__ == "__main__":
    main()
