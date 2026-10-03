"""Features around a check: images, authentic alternatives, polite replies, hadith of the day.

All of them keep the same rule as the checker: anything shown as a verse or hadith
comes from the indexed sources, never from a language model's memory.
"""
import base64
import datetime
import re
import urllib.request

import logging

import numpy as np

import ai
from arabic import normalize
from english import normalize_en
from matcher import Matcher
from verify import grade_summary, link_for, names_unknown_book, ref_of

log = logging.getLogger("tabayyan.extras")
MAX_IMAGE_BYTES = 8 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

TEXT = {
    "ar": {
        "no_ai": "هذه الميزة تحتاج خدمة الذكاء الاصطناعي، وهي غير متاحة الآن.",
        "no_text": "لم نجد في الصورة نصًا يمكن قراءته.",
        "bad_image": "تعذر فتح الصورة. جرّب صورة بصيغة JPG أو PNG.",
        "none_found": "لم نجد في المصادر نصًا صحيحًا قريبًا من هذا المعنى.",
    },
    "en": {
        "no_ai": "This feature needs the AI service, which is not available right now.",
        "no_text": "We could not find readable text in the image.",
        "bad_image": "Could not open the image. Try a JPG or PNG image.",
        "none_found": "We did not find an authentic text with a close meaning in the sources.",
    },
}


# ---------- images ----------

def load_image(data: str | None, url: str | None) -> tuple[str, str] | None:
    """Returns (base64 data, media type) from a data URL / base64 string, or by downloading url."""
    if data:
        m = re.match(r"data:(image/[\w+.-]+);base64,(.*)", data, re.S)
        media, b64 = (m.group(1), m.group(2)) if m else ("image/jpeg", data)
        raw = base64.b64decode(b64, validate=False)
    elif url and re.match(r"https?://", url):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Tabayyan"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            media = resp.headers.get_content_type()
            raw = resp.read(MAX_IMAGE_BYTES + 1)
    else:
        return None
    if len(raw) > MAX_IMAGE_BYTES or not raw:
        return None
    # Trust the bytes, not the label.
    if raw[:3] == b"\xff\xd8\xff":
        media = "image/jpeg"
    elif raw[:8] == b"\x89PNG\r\n\x1a\n":
        media = "image/png"
    elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        media = "image/webp"
    elif raw[:4] == b"GIF8":
        media = "image/gif"
    else:
        return None
    return base64.b64encode(raw).decode(), media


# ---------- authentic alternatives ----------

def _strong(r: dict) -> bool:
    if r["type"] == "quran":
        return "ayah_end" not in r and r.get("translator") in (None, "Saheeh International")
    return grade_summary(r.get("grades", []))[1] == "strong"


def _top(sims: np.ndarray, n: int) -> list[int]:
    n = min(n, len(sims) - 1)
    idx = np.argpartition(-sims, n)[:n]
    return [int(i) for i in idx[np.argsort(-sims[idx])]]


def retrieve(matcher: Matcher, terms: dict, limit: int = 16, kind: str | None = None) -> list[dict]:
    """Strongly graded hadiths and verses whose wording is closest to the search terms.
    terms: {"en": [English phrasings of the meaning], "ar": "Arabic keywords"}."""
    scored: dict[int, tuple[float, dict]] = {}

    def add(sims, top, rows, weight):
        for rank, i in enumerate(top):
            r = rows[i]
            if not _strong(r) or sims[i] <= 0 or (kind and r["type"] != kind):
                continue
            # reciprocal rank, so each phrasing contributes its own best matches
            score = weight / (rank + 5)
            prev = scored.get(r["id"], (0.0, r))[0]
            scored[r["id"]] = (prev + score, r)

    # Very short texts ("Noble and dutiful") match a single word too easily; damp them.
    lengths = getattr(matcher, "_en_len", None)
    if lengths is None:
        lengths = matcher._en_len = np.minimum(1.0, np.diff(matcher.en_matrix.indptr) / 12.0) ** 0.5
    for phrase in terms.get("en") or []:
        sims = (matcher.en_matrix @ matcher.en_vec.transform([normalize_en(phrase)]).T).toarray().ravel() * lengths
        top = _top(sims, 120)
        add(sims, top, matcher.fetch_en(top), 1.0)
    if terms.get("ar"):
        sims = (matcher.matrix @ matcher.vec.transform([normalize(terms["ar"])]).T).toarray().ravel()
        top = _top(sims, 80)
        add(sims, top, matcher.fetch(top), 0.4)
    best = sorted(scored.values(), key=lambda x: -x[0])[:limit]
    return [r for _, r in best]


def _clean(text: str, refs: str) -> bool:
    """No book names or numbers that are not in the given references."""
    if names_unknown_book(text, refs):
        return False
    nums = re.findall(r"\d+", text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")))
    return all(n in re.findall(r"\d+", refs) for n in nums)


def alternatives(matcher: Matcher, text: str, lang: str) -> dict:
    t = TEXT[lang]
    terms = ai.search_terms(text)
    if terms is None:
        return {"available": False, "items": [], "message": t["no_ai"]}
    records = retrieve(matcher, terms)
    if not records:
        return {"available": True, "items": [], "message": t["none_found"]}
    cands = [{"id": i, "ref": r["ref"], "arabic": r["text"], "english": r.get("english", "")}
             for i, r in enumerate(records)]
    picks = ai.pick_alternatives(text, cands, lang)
    if picks is None:
        return {"available": False, "items": [], "message": t["no_ai"]}
    items = []
    for p in picks[:2]:
        try:
            r = records[int(p.get("id"))]
        except (TypeError, ValueError, IndexError):
            continue  # guard: only our own candidates
        excerpt = str(p.get("excerpt", "")).strip()
        # guard: the excerpt must really be part of the source text
        if len(normalize(excerpt).split()) < 3 or normalize(excerpt) not in normalize(r["text"]):
            excerpt = r["text"] if len(r["text"]) <= 400 else r["text"][:400] + "…"
        why = str(p.get("why", "")).strip()
        if not _clean(why, ""):
            why = ""
        label, status = grade_summary(r.get("grades", []), lang)
        items.append({
            "type": r["type"],
            "ref": ref_of(r, lang),
            "excerpt": excerpt,
            "english": r.get("english", ""),
            "why": why,
            "grade_summary": label if r["type"] == "hadith" else None,
            "link": link_for(r),
        })
    return {"available": True, "items": items, "message": None if items else t["none_found"]}


# ---------- polite reply ----------

def _facts(result: dict, alternative: dict | None) -> dict:
    m = result.get("match") or {}
    correct = " ".join(w["word"] for w in m.get("words", []) if w.get("status") != "context")
    return {
        "verdict": result.get("verdict"),
        "checked_text": result.get("quote", ""),
        "claimed_as": result.get("claimed"),
        "reference": m.get("ref"),
        "grading": m.get("grade_summary"),
        "grading_status": m.get("grade_status"),
        "translation": m.get("translator"),
        "correct_text": correct if result.get("verdict") == "partial" else None,
        "link": m.get("link"),
        "authentic_alternative": alternative and {k: alternative.get(k) for k in ("ref", "excerpt", "link")},
    }


def template_reply(f: dict, lang: str) -> str:
    alt = f.get("authentic_alternative")
    if lang == "en":
        if f["verdict"] == "found" and f.get("grading_status") == "weak":
            s = (f"JazakAllahu khayran for sharing. This text is in {f['reference']}, but scholars graded it weak, "
                 "so it is safer not to attribute it to the Prophet ﷺ with certainty.")
        elif f["verdict"] == "found":
            s = f"JazakAllahu khayran for sharing 🌿 This text is authentic and found in {f['reference']}."
        elif f["verdict"] == "partial":
            s = (f"JazakAllahu khayran. The original in {f['reference']} is worded a little differently. "
                 f"The correct text is:\n“{f['correct_text']}”")
        elif f.get("claimed_as") == "athar":
            s = ("JazakAllahu khayran. This saying is attributed to a companion or scholar, not to the Prophet ﷺ, "
                 "so it should not be shared as a hadith.")
        else:
            s = ("JazakAllahu khayran for wanting to spread good. I could not find this text in the main hadith "
                 "collections, so it is safer not to attribute it to the Prophet ﷺ until its source is known.")
        if alt and f["verdict"] != "found":
            s += f"\nAn authentic text with a similar meaning: “{alt['excerpt']}” ({alt['ref']})\n{alt['link']}"
        elif f.get("link"):
            s += f"\n{f['link']}"
        return s
    if f["verdict"] == "found" and f.get("grading_status") == "weak":
        s = (f"جزاك الله خيرًا على حرصك. هذا النص موجود في {f['reference']}، لكن العلماء ضعّفوه، "
             "فالأحوط ألا يُنسب إلى النبي ﷺ بجزم.")
    elif f["verdict"] == "found":
        s = f"جزاك الله خيرًا على المشاركة 🌿 النص صحيح وموجود في {f['reference']}."
    elif f["verdict"] == "partial":
        s = f"جزاك الله خيرًا. النص الأصلي في {f['reference']} لفظه مختلف قليلًا، وهذا نصه الصحيح:\n«{f['correct_text']}»"
    elif f.get("claimed_as") == "athar":
        s = "جزاك الله خيرًا. هذا القول منسوب إلى أحد الصحابة أو العلماء، وليس حديثًا نبويًا، فلا يُنشر على أنه حديث."
    else:
        s = ("جزاك الله خيرًا على حرصك على الخير. بحثت عن هذا النص في كتب الحديث المعروفة ولم أجده، "
             "فالأحوط ألا ننسبه إلى النبي ﷺ حتى نعرف مصدره.")
    if alt and f["verdict"] != "found":
        s += f"\nوفي معناه نص صحيح: «{alt['excerpt']}» ({alt['ref']})\n{alt['link']}"
    elif f.get("link"):
        s += f"\n{f['link']}"
    return s


def reply(result: dict, alternative: dict | None, lang: str) -> dict:
    f = _facts(result, alternative)
    text = ai.write_reply(f, lang)
    refs = " ".join(str(x) for x in (f.get("reference"), f.get("link"),
                                     alternative and alternative.get("ref"), alternative and alternative.get("link"),
                                     alternative and alternative.get("excerpt"), f.get("correct_text")) if x)
    if text and _clean(text, refs):
        return {"reply": text, "source": "claude"}
    if text:
        log.warning("reply rejected by guard: %r | refs: %r", text[:300], refs[:300])
    return {"reply": template_reply(f, lang), "source": "template"}


# ---------- hadith of the day ----------

def daily(matcher: Matcher, lang: str, day: datetime.date | None = None) -> dict:
    """One of Imam an-Nawawi's Forty Hadith, a different one each day, straight from the data."""
    rows = matcher.db.execute("SELECT * FROM records WHERE book = 'nawawi' ORDER BY number").fetchall()
    day = day or datetime.date.today()
    r = matcher._row(rows[day.toordinal() % len(rows)])
    return {"ref": ref_of(r, lang), "text": r["text"], "english": r.get("english", ""), "link": link_for(r)}


# ---------- searching the sources by topic ----------

_PREFIXES = ("وال", "فال", "بال", "كال", "لل", "ال", "و", "ف", "ب", "ل", "ك")
_SUFFIXES = ("هما", "كما", "ين", "ون", "ان", "ات", "ها", "هم", "كم", "نا", "ه", "ي", "ك")


def _strip_prefix(w: str) -> str:
    for p in _PREFIXES:
        if w.startswith(p) and len(w) - len(p) >= 2:
            return w[len(p):]
    return w


def _stem(w: str) -> str:
    """Very light Arabic stemming, enough to match 'الوالدين' with 'بوالديه'."""
    w = _strip_prefix(w)
    for x in _SUFFIXES:
        if w.endswith(x) and len(w) - len(x) >= 3:
            w = w[: -len(x)]
            break
    return w


def _search_arabic(matcher: Matcher, q: str, kind: str | None, limit: int) -> list[dict]:
    from matcher import STOPWORDS
    words = [w for w in normalize(q).split() if w not in STOPWORDS] or normalize(q).split()
    stems = [_stem(w) for w in words][:6]
    bases = [_strip_prefix(w) for w in words][:6]
    if not stems:
        return []
    # candidates: every text containing all the stems as substrings (one SQL scan)
    sql = "SELECT * FROM records WHERE ayah_end IS NULL" + "".join(" AND norm LIKE ?" for _ in stems)
    args = [f"%{x}%" for x in stems]
    if kind in ("quran", "hadith"):
        sql += " AND type = ?"
        args.append(kind)
    rows = [matcher._row(r) for r in matcher.db.execute(sql + " LIMIT 4000", args).fetchall()]
    scored = []
    for r in rows:
        words_ = r["norm"].split()
        if r["type"] == "hadith":
            # match the Prophet's words, not narrator names in the chain
            start = next((i + 2 for i in range(len(words_) - 1)
                          if words_[i] in ("رسول", "النبي") or (words_[i] == "قال" and i > len(words_) * 0.3)), 0)
            words_ = words_[start:]
        doc = [_stem(w) for w in words_]
        doc_bases = {_strip_prefix(w) for w in words_}

        def hit(x):
            return [d for d in doc if d == x or (len(x) >= 3 and d.startswith(x))]
        hits = [hit(x) for x in stems]
        if all(hits):
            exact = sum(b in doc_bases for b in bases)  # the word itself, not just its root form
            density = sum(len(h) for h in hits) / (len(doc) + 8)
            scored.append((-exact, -density, len(doc), r))
    scored.sort(key=lambda x: x[:3])
    return [r for *_, r in scored[: limit * 4]]


def search_sources(matcher: Matcher, query: str, lang: str, kind: str | None = None,
                   strong_only: bool = True, limit: int = 20) -> dict:
    """Verses and authentic hadiths about a topic (Arabic or English).
    With the AI service, Claude rewrites the topic into search phrases (it never supplies texts);
    without it, a plain word search. Results always come from the indexed sources."""
    from english import is_english
    q = query.strip()[:300]
    if not q:
        return {"items": [], "mode": None}
    mode = "words"
    records = None
    if strong_only:
        terms = ai.topic_terms(q)
        if terms and (terms["en"] or terms["ar"]):
            if is_english(q):
                terms["en"] = [q] + terms["en"]
            records = retrieve(matcher, terms, limit=limit, kind=kind)
            mode = "meaning"
    if records is None:
        if is_english(q):
            sims = (matcher.en_matrix @ matcher.en_vec.transform([normalize_en(q)]).T).toarray().ravel()
            if kind in ("quran", "hadith"):
                sims[matcher.en_types != (0 if kind == "quran" else 1)] = -1
            top = [i for i in _top(sims, 300) if sims[i] > 0]
            rows = matcher.fetch_en(top)
            records = [rows[i] for i in top
                       if not (rows[i]["type"] == "quran" and rows[i].get("translator") != "Saheeh International")]
        else:
            records = _search_arabic(matcher, q, kind, limit)
    items, seen = [], set()
    for r in records:
        if r["id"] in seen or "ayah_end" in r:
            continue
        label, status = grade_summary(r.get("grades", []), lang)
        if strong_only and r["type"] == "hadith" and status != "strong":
            continue
        seen.add(r["id"])
        items.append({
            "type": r["type"],
            "ref": ref_of(r, lang),
            "text": r["text"],
            "english": r.get("english", ""),
            "grade_summary": label if r["type"] == "hadith" else None,
            "grade_status": status if r["type"] == "hadith" else None,
            "link": link_for(r),
        })
        if len(items) >= limit:
            break
    return {"items": items, "mode": mode}
