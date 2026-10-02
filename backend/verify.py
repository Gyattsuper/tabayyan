"""Turn a message into verification results the interface can show.

Pipeline: extract quotes (Claude, or rules as fallback) -> match each quote
against the sources -> verdict, reference, correct text, word diff,
gradings, warnings -> explanation.
"""
import re
from collections import Counter
from difflib import SequenceMatcher
from urllib.parse import quote as urlquote

from rapidfuzz import fuzz

import ai
from arabic import normalize
from extract import candidates, claimed_kind
from matcher import FOUND, Match, Matcher, verdict

STRONG = {"صحيح", "حسن"}
WEAK = {"ضعيف", "موضوع", "منكر", "باطل", "شاذ"}
HONORIFIC_WORDS = set(normalize("صلى الله عليه وسلم رضي عنه عنها عنهما السلام الصلاة").split())

# sunnah.com numbering matches the dataset for these collections (spot-checked).
SUNNAH_DIRECT = {"bukhari": "bukhari", "abudawud": "abudawud", "tirmidhi": "tirmidhi",
                 "nasai": "nasai", "ibnmajah": "ibnmajah", "nawawi": "nawawi40", "qudsi": "qudsi40"}

SCOPE_NOTE = ("البحث يشمل القرآن الكريم وتسعة من كتب الحديث: الصحيحين والسنن الأربع وموطأ مالك "
              "والأربعين النووية والأحاديث القدسية.")


# ---------- presentation helpers ----------

def grade_summary(grades: list[dict]) -> tuple[str, str]:
    """(label, status) where status is strong | weak | disputed | none."""
    labels = [g["grade"] for g in grades]
    if not labels:
        return "لم تُذكر له درجة في المصدر", "none"
    strong = [l for l in labels if l in STRONG]
    weak = [l for l in labels if l in WEAK]
    if strong and weak:
        return "مختلف في درجته", "disputed"
    if weak:
        return Counter(weak).most_common(1)[0][0], "weak"
    if strong:
        return Counter(strong).most_common(1)[0][0], "strong"
    return Counter(labels).most_common(1)[0][0], "none"


def link_for(r: dict) -> str:
    if r["type"] == "quran":
        return f"https://quran.com/{r['surah']}/{r['ayah']}"
    if r["book"] in SUNNAH_DIRECT:
        return f"https://sunnah.com/{SUNNAH_DIRECT[r['book']]}:{r['number']}"
    return f"https://sunnah.com/search?q={urlquote(' '.join(r['norm'].split()[:8]))}"


def source_words(text: str) -> list[tuple[str, str]]:
    """Original words paired with their normalized form."""
    return [(w, normalize(w)) for w in text.split()]


def locate_span(record: dict, span_norm: str, quote_norm: str) -> tuple[list[tuple[str, str]], int, int]:
    """Find the matched span inside the original (diacritized) text.

    Returns the word list and [start, end) indices of the span.
    """
    words = source_words(record["text"])
    keep = [(i, n) for i, (_, n) in enumerate(words) if n]
    joined, starts = "", []
    for i, n in keep:
        starts.append(len(joined))
        joined += n + " "
    a = fuzz.partial_ratio_alignment(span_norm, joined)
    first = next((k for k, s in enumerate(starts) if s + len(keep[k][1]) > a.dest_start), 0)
    last = next((k for k, s in enumerate(starts) if s >= a.dest_end), len(keep)) - 1
    last = max(first, last)
    # The alignment window can spill onto neighbouring words ("يقول", "قال").
    # Trim edge words that don't resemble any word of the quote.
    qw = quote_norm.split()
    def related(n):
        return any(fuzz.ratio(n, w) >= 70 for w in qw)
    while first < last and not related(keep[first][1]):
        first += 1
    while last > first and not related(keep[last][1]):
        last -= 1
    return words, keep[first][0], keep[last][0] + 1


def word_diff(quote: str, source_norm_words: list[str]) -> tuple[list[dict], set[int]]:
    """Mark the user's words (as they typed them) as same/changed/extra, and
    return which source word indices were missing or different."""
    typed = [(w, normalize(w)) for w in quote.split()]
    typed = [(w, n) for w, n in typed if n]
    q = [n for _, n in typed]
    sm = SequenceMatcher(a=q, b=source_norm_words, autojunk=False)
    out, src_changed = [], set()
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        status = {"equal": "same", "replace": "changed", "delete": "extra"}.get(tag)
        if status:
            out += [{"word": w, "status": status} for w, _ in typed[i1:i2]]
        if tag in ("replace", "insert"):  # insert: source words the user left out
            src_changed.update(range(j1, j2))
    return out, src_changed


# ---------- building results ----------

def build_result(quote: str, claimed: str | None, matches: list[Match], lang: str) -> dict:
    v = verdict(matches)
    res = {"verdict": v, "quote": quote, "claimed": claimed, "match": None,
           "diff": None, "others": [], "warnings": []}

    if v != "not_found":
        m = matches[0]
        r = m.record
        words, a, b = locate_span(r, m.span, normalize(quote))
        # compare only real words (skip punctuation-only tokens), remembering their positions
        real = [k for k in range(a, b) if words[k][1]]
        diff, changed_idx = word_diff(quote, [words[k][1] for k in real])
        changed = {real[i] for i in changed_idx}
        # Mark the source span word by word so the interface can highlight differences.
        highlighted = []
        for k, (w, n) in enumerate(words):
            inside = a <= k < b
            status = "context"
            if inside:
                status = "changed" if k in changed and n not in HONORIFIC_WORDS else "match"
            highlighted.append({"word": w, "status": status})
        label, status = grade_summary(r.get("grades", []))
        res["match"] = {
            "type": r["type"],
            "ref": r["ref"],
            "words": highlighted,
            "english": r.get("english", ""),
            "grades": r.get("grades", []),
            "grade_summary": label if r["type"] == "hadith" else None,
            "grade_status": status if r["type"] == "hadith" else None,
            "link": link_for(r),
        }
        res["diff"] = diff
        # Other places the same text appears
        seen = {r["ref"]}
        for o in matches[1:]:
            if (o.score >= FOUND and o.coverage == 1.0 and o.record["type"] == r["type"]
                    and o.record["ref"] not in seen and "ayah_end" not in o.record):
                seen.add(o.record["ref"])
                res["others"].append({"ref": o.record["ref"], "link": link_for(o.record)})

        if claimed == "hadith" and r["type"] == "quran":
            res["warnings"].append("هذا النص آية من القرآن الكريم، وليس حديثًا نبويًا كما ورد في الرسالة.")
        if claimed == "athar" and r["type"] == "quran":
            res["warnings"].append("هذا النص آية من القرآن الكريم، وليس من كلام من نُسب إليه في الرسالة.")
        if claimed == "quran" and r["type"] == "hadith":
            res["warnings"].append("هذا النص ليس آية قرآنية، وإنما ورد في كتب الحديث.")
        if r["type"] == "hadith" and status == "weak":
            res["warnings"].append("النص موجود في المصدر، لكن العلماء المذكورين حكموا عليه بالضعف، فلا تصح نسبته إلى النبي ﷺ بثقة.")
        if r["type"] == "hadith" and status == "disputed":
            res["warnings"].append("اختلف العلماء في درجة هذا الحديث، والأحكام معروضة كما وردت.")
    elif claimed == "athar":
        # A companion's or scholar's saying: many are reported in books we don't index,
        # so "not found" here says nothing about whether the attribution is right.
        res["warnings"].append("الرسالة تنسب هذا القول إلى أحد الصحابة أو العلماء، لا إلى النبي ﷺ. "
                               "تبيّن يبحث في القرآن وكتب الحديث فقط، وكثير من أقوال الصحابة والعلماء مروية في "
                               "كتب أخرى لا يشملها البحث، فعدم وجوده هنا لا يعني أن نسبته خاطئة. "
                               "للتحقق منه ارجع إلى كتب الآثار وأهل العلم، ولا تنسبه إلى النبي ﷺ.")
    else:
        res["warnings"].append("لم نجد هذا النص في المصادر التي نبحث فيها. هذا وحده لا يعني أنه مكذوب، "
                               "لكن لا تنشره منسوبًا إلى القرآن أو السنة قبل سؤال أهل العلم.")
    res["scope"] = SCOPE_NOTE
    expl = ai.explain(res, lang)
    res["explanation_source"] = "claude" if expl and explanation_is_grounded(expl, res) else "template"
    res["explanation"] = expl if res["explanation_source"] == "claude" else template_explanation(res)
    return res


BOOK_NAMES = ["البخاري", "مسلم", "أبي داود", "أبو داود", "الترمذي", "النسائي", "ابن ماجه", "مالك", "الموطأ",
              "النووية", "القدسية", "أحمد", "المسند", "البيهقي", "الطبراني", "الحاكم", "Bukhari", "Muslim",
              "Dawud", "Tirmidhi", "Nasa", "Majah", "Malik", "Nawawi", "Ahmad"]


def explanation_is_grounded(expl: str, res: dict) -> bool:
    """Reject a model explanation that names a book or number not in the result."""
    allowed = " ".join([res["match"]["ref"]] + [o["ref"] for o in res["others"]]) if res["match"] else ""
    allowed_n = normalize(allowed)
    for name in BOOK_NAMES:
        n = normalize(name) or name.lower()
        if (n in normalize(expl) or name.lower() in expl.lower()) and n not in allowed_n and name not in allowed:
            return False
    for num in re.findall(r"\d+", expl.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))):
        if num not in allowed:
            return False
    return True


def template_explanation(res: dict) -> str:
    m = res["match"]
    if res["verdict"] == "found":
        base = f"النص موجود في {m['ref']}."
        if m["type"] == "hadith":
            base += f" درجته: {m['grade_summary']}."
        return base
    if res["verdict"] == "partial":
        n = sum(d["status"] != "same" for d in res["diff"]) or 1
        count = {1: "كلمة واحدة تختلف", 2: "كلمتان تختلفان"}.get(n, f"{n} كلمات تختلف" if n <= 10 else f"{n} كلمة تختلف")
        return (f"النص قريب مما في {m['ref']}، لكن فيه {count} عن الأصل، وهي مظللة في النص الصحيح. "
                "انقل النص الصحيح إن أردت نشره.")
    return ""  # the not-found warning already says everything


_RANK = {"found": 2, "partial": 1, "not_found": 0}


def verify(matcher: Matcher, message: str, lang: str = "ar") -> dict:
    message = message.strip()[:4000]
    extracted = ai.extract_quotes(message)
    extractor = "claude" if extracted is not None else "rules"

    results = []
    if extracted:
        for q in extracted[:3]:
            best = None
            for cand in candidates(q["text"]):
                ms = matcher.search(cand)
                key = (_RANK[verdict(ms)], ms[0].score if ms else 0)
                if best is None or key > best[0]:
                    best = (key, cand, ms)
            if best is None:
                continue
            claimed = q["claimed"] or claimed_kind(message)
            results.append(build_result(best[1], claimed, best[2], lang))

    if not results:
        # Rule-based: try each candidate span, keep the strongest.
        best = None
        for cand in candidates(message):
            ms = matcher.search(cand)
            key = (_RANK[verdict(ms)], ms[0].score if ms else 0)
            if best is None or key > best[0]:
                best = (key, cand, ms)
            if key[0] == 2:
                break
        if best is not None:
            results.append(build_result(best[1], claimed_kind(message), best[2], lang))

    out = {"extractor": extractor, "results": results}
    if not results:
        out["message"] = "لم نجد في النص كلمات عربية يمكن البحث عنها. الصق نص الآية أو الحديث نفسه."
    return out
