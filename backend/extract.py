"""Pull the quoted verse or hadith out of a messy message.

The main extractor (added during the challenge) uses the Claude API. This
rule-based version is the fallback when the API is unavailable, and it is
also used to double-check the model's output.
"""
import re

from arabic import normalize

# Phrases that introduce a quote: "قال رسول الله ﷺ", "قال تعالى", "عن النبي ..."
_INTRO = re.compile(
    r"(?:قال|يقول|وقال|عن)\s+(?:رسول\s+الله|النبي|الرسول|المصطفى|نبينا|الله\s+تعالى|تعالى|الله\s+عز\s+وجل|سبحانه)"
    r"(?:\s*ﷺ|\s*صل[ىي]\s+الله\s+عليه\s+وسلم|\s*عليه\s+الصلاة\s+والسلام|\s*عز\s+وجل|\s*سبحانه\s+وتعالى)?\s*[:：]?"
)
_QUOTES = re.compile(r"[«\"“﴿]([^»\"”﴾]{8,})[»\"”﴾]")
_SENTENCE_END = re.compile(r"[.!؟?\n]|انشر|شارك|ارسل|أرسل|تؤجر")

_CLAIMS_HADITH = re.compile(r"رسول\s+الله|النبي|الرسول|المصطفى|نبينا|ﷺ|صل[ىي]\s+الله\s+عليه\s+وسلم|حديث")
_CLAIMS_QURAN = re.compile(r"قال\s+(?:الله\s+)?تعالى|الله\s+عز\s+وجل|سبحانه|آية|الآية|القرآن|﴿")
# Sayings attributed to a companion or a scholar rather than to the Prophet ﷺ.
_CLAIMS_ATHAR = re.compile(
    r"رض[يى]\s+الله\s+عن|رحمه\s+الله|الصحاب[يةه]|\bالإمام\b|"
    r"\b(?:عمر|عثمان|أبو\s+بكر|أبي\s+بكر|الصديق|الفاروق|علي\s+بن\s+أبي\s+طالب|ابن\s+عباس|ابن\s+مسعود|ابن\s+عمر|"
    r"عائشة|أبو\s+هريرة|معاذ|سلمان|أبو\s+ذر|الحسن\s+البصري|الشافعي|مالك\s+بن\s+أنس|أحمد\s+بن\s+حنبل|ابن\s+تيمية|ابن\s+القيم)\b"
)


def claimed_kind(text: str) -> str | None:
    """What the message says the quote is: 'hadith', 'quran', 'athar' (a companion's or
    scholar's saying), or None if it doesn't say."""
    h, q = _CLAIMS_HADITH.search(text), _CLAIMS_QURAN.search(text)
    if not h and not q and _CLAIMS_ATHAR.search(text):
        return "athar"
    if h and not q:
        return "hadith"
    if q and not h:
        return "quran"
    if h and q:
        return "hadith" if h.start() < q.start() else "quran"
    return None


def candidates(text: str) -> list[str]:
    """Possible quote spans, most specific first. Always ends with the full text."""
    out = []
    for m in _QUOTES.finditer(text):
        out.append(m.group(1))
    for m in _INTRO.finditer(text):
        rest = text[m.end():]
        end = _SENTENCE_END.search(rest)
        out.append(rest[: end.start()] if end else rest)
    # Any other "...: quote" (e.g. a saying introduced by someone's name).
    for m in re.finditer(r"[:：]\s*", text):
        rest = text[m.end():]
        end = _SENTENCE_END.search(rest)
        out.append(rest[: end.start()] if end else rest)
    out.append(text)
    seen, uniq = set(), []
    for c in out:
        n = normalize(c)
        if n and n not in seen:
            seen.add(n)
            uniq.append(c.strip())
    return uniq
