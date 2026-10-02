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


def retrieve(matcher: Matcher, terms: dict, limit: int = 16) -> list[dict]:
    """Strongly graded hadiths and verses whose wording is closest to the search terms.
    terms: {"en": [English phrasings of the meaning], "ar": "Arabic keywords"}."""
    scored: dict[int, tuple[float, dict]] = {}

    def add(sims, top, rows, weight):
        for rank, i in enumerate(top):
            r = rows[i]
            if not _strong(r) or sims[i] <= 0:
                continue
            # reciprocal rank, so each phrasing contributes its own best matches
            score = weight / (rank + 5)
            prev = scored.get(r["id"], (0.0, r))[0]
            scored[r["id"]] = (prev + score, r)

    for phrase in terms.get("en") or []:
        sims = (matcher.en_matrix @ matcher.en_vec.transform([normalize_en(phrase)]).T).toarray().ravel()
        top = _top(sims, 120)
        add(sims, top, matcher.fetch_en(top), 1.0)
    if terms.get("ar"):
        sims = (matcher.matrix @ matcher.vec.transform([normalize(terms["ar"])]).T).toarray().ravel()
        top = _top(sims, 80)
        add(sims, top, matcher.fetch(top), 0.8)
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
