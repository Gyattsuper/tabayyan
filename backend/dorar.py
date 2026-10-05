"""Scholars' rulings from the Dorar al-Saniyyah hadith encyclopedia (dorar.net), for texts that are
not in the nine collections Tabayyan indexes. Dorar covers about 300,000 hadiths with the ruling of
each hadith scholar; it is one of the sources recommended in the challenge's reference framework.

Only results whose text really contains the quote are kept, and every field is shown as Dorar gives
it (no model involved). Any network problem simply returns no results.
"""
import html
import json
import logging
import re
import urllib.parse
import urllib.request
from functools import lru_cache

from rapidfuzz import fuzz

from arabic import normalize

log = logging.getLogger(__name__)
API = "https://dorar.net/dorar_api.json?skey="
SEARCH_PAGE = "https://dorar.net/hadith/search?q="
LABELS = {"الراوي": "narrator", "المحدث": "scholar", "المصدر": "source",
          "الصفحة أو الرقم": "page", "خلاصة حكم المحدث": "grading"}
_WEAK = re.compile(r"ضعيف|موضوع|باطل|منكر|لا أصل|ليس له أصل|كذب|لا يصح|لا يثبت|واه|مكذوب|شاذ|متروك")
_STRONG = re.compile(r"صحيح|حسن|ثابت|جيد")


def _clean(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(text)).strip(" -:‏‎")


def parse(result_html: str) -> list[dict]:
    items = []
    blocks = re.findall(r'<div class="hadith"[^>]*>(.*?)</div>\s*<div class="hadith-info">(.*?)</div>',
                        result_html, re.S)
    for text_html, info_html in blocks:
        text = re.sub(r"^\d+\s*-\s*", "", _clean(text_html)).rstrip(" .")
        item = {"text": text}
        parts = re.split(r'<span class="info-subtitle">\s*([^<]+?)\s*:?\s*</span>', info_html)
        for label, value in zip(parts[1::2], parts[2::2]):
            key = LABELS.get(label.strip().rstrip(":").strip())
            if key:
                item[key] = _clean(value)
        if item.get("grading") and item.get("scholar"):
            items.append(item)
    return items


def status(grading: str) -> str:
    if _WEAK.search(grading):
        return "weak"
    if _STRONG.search(grading):
        return "strong"
    return "other"


def _contains(quote: str, text: str) -> bool:
    """True when the hadith text contains the quote (allowing small spelling differences)."""
    q, t = normalize(quote), normalize(text)
    if not q or not t:
        return False
    if len(q) <= len(t):
        return fuzz.partial_ratio(q, t) >= 88
    return fuzz.ratio(q, t) >= 88


@lru_cache(maxsize=512)
def _fetch(query: str) -> str:
    req = urllib.request.Request(API + urllib.parse.quote(query), headers={"User-Agent": "Tabayyan/1.0"})
    with urllib.request.urlopen(req, timeout=6) as resp:
        return json.loads(resp.read().decode("utf-8"))["ahadith"]["result"]


def lookup(quote: str, limit: int = 4) -> dict:
    quote = re.sub(r"\s+", " ", quote or "").strip()[:300]
    out = {"items": [], "link": SEARCH_PAGE + urllib.parse.quote(quote)}
    if len(normalize(quote).split()) < 3:
        return out
    try:
        items = parse(_fetch(quote))
    except Exception:
        log.exception("Dorar lookup failed")
        out["error"] = True
        return out
    seen = set()
    for it in items:
        key = (it.get("scholar"), it.get("grading"))
        if key in seen or not _contains(quote, it["text"]):
            continue
        seen.add(key)
        it["status"] = status(it["grading"])
        out["items"].append(it)
        if len(out["items"]) >= limit:
            break
    return out
