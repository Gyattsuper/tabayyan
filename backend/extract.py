"""Pull the quoted verse or hadith out of a messy message.

The main extractor (added during the challenge) uses the Claude API. This
rule-based version is the fallback when the API is unavailable, and it is
also used to double-check the model's output.
"""
import re

from arabic import normalize
from english import is_english, normalize_en


def normalize_any(text: str) -> str:
    return normalize_en(text) if is_english(text) else normalize(text)


# Phrases that introduce a quote: "قال رسول الله ﷺ", "قال تعالى", "عن النبي ..."
_INTRO = re.compile(
    r"(?:قال|يقول|وقال|عن)\s+(?:رسول\s+الله|النبي|الرسول|المصطفى|نبينا|الله\s+تعالى|تعالى|الله\s+عز\s+وجل|سبحانه)"
    r"(?:\s*ﷺ|\s*صل[ىي]\s+الله\s+عليه\s+وسلم|\s*عليه\s+الصلاة\s+والسلام|\s*عز\s+وجل|\s*سبحانه\s+وتعالى)?\s*[:：]?"
)
_QUOTES = re.compile(r"[«\"“﴿]([^»\"”﴾]{8,})[»\"”﴾]")
# English introductions: "The Prophet (ﷺ) said:", "Allah says in the Quran:"
_INTRO_EN = re.compile(
    r"(?:said|says|stated|states)\s*(?:\([^)]*\))?\s*(?:in\s+the\s+(?:holy\s+)?qur.?an)?\s*[:,]",
    re.IGNORECASE,
)
_SENTENCE_END = re.compile(r"[.!؟?\n]|انشر|شارك|ارسل|أرسل|تؤجر|(?i:\bplease\s+share|\bshare\s+this)")
# Where a forwarded message's own words start again ("انشروها", "please share"), or a new line.
_MESSAGE_END = re.compile(r"\n|انشر|شارك|ارسل|أرسل|تؤجر|(?i:\bplease\s+share|\bshare\s+this|\bforward\s+this)")
# 'single-quoted' English quotes (apostrophes inside words like "Allah's" are skipped)
_QUOTES_SINGLE = re.compile(r"(?:^|(?<=[\s:,]))[‘']([^‘’']{8,}?(?:'[a-z][^‘’']*)*)[’'](?=[\s.,!?]|$)")

_CLAIMS_HADITH = re.compile(r"رسول\s+الله|النبي|الرسول|المصطفى|نبينا|ﷺ|صل[ىي]\s+الله\s+عليه\s+وسلم|حديث|"
                            r"(?i:\bprophet\b|messenger\s+of\s+allah|allah'?s\s+messenger|\bpbuh\b|\bhadith\b|"
                            r"peace\s+be\s+upon\s+him|\bsunnah\b)")
_CLAIMS_QURAN = re.compile(r"قال\s+(?:الله\s+)?تعالى|الله\s+عز\s+وجل|سبحانه|آية|الآية|القرآن|﴿|"
                           r"(?i:\bqur.?an\b|\bkoran\b|\bverse\b|\bayah\b|\bsurah?\b|allah\s+says|god\s+says)")
# Sayings attributed to a companion or a scholar rather than to the Prophet ﷺ.
_CLAIMS_ATHAR = re.compile(
    r"رض[يى]\s+الله\s+عن|رحمه\s+الله|الصحاب[يةه]|\bالإمام\b|"
    r"\b(?:عمر|عثمان|أبو\s+بكر|أبي\s+بكر|الصديق|الفاروق|علي\s+بن\s+أبي\s+طالب|ابن\s+عباس|ابن\s+مسعود|ابن\s+عمر|"
    r"عائشة|أبو\s+هريرة|معاذ|سلمان|أبو\s+ذر|الحسن\s+البصري|الشافعي|مالك\s+بن\s+أنس|أحمد\s+بن\s+حنبل|ابن\s+تيمية|ابن\s+القيم)\b|"
    r"(?i:\bumar\b|\bomar\b|abu\s+bakr|\buthman\b|ali\s+ibn\s+abi\s+talib|ibn\s+abbas|ibn\s+mas.?ud|\baisha\b|"
    r"abu\s+hurairah|\(ra\)|\(r\.a\.?\)|may\s+allah\s+be\s+pleased|\bimam\b|al-?shafi|ibn\s+taymiyyah|"
    r"ibn\s+al-?qayyim|hasan\s+al-?basri)"
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
    for m in list(_QUOTES.finditer(text)) + list(_QUOTES_SINGLE.finditer(text)):
        out.append(m.group(1))
    # Text after an introduction ("قال رسول الله ﷺ:", "The Prophet said:") or any other colon,
    # up to the end of that sentence, and up to the end of the quoted part of the message
    # (quotes are often several sentences long).
    intros = list(_INTRO.finditer(text)) + list(_INTRO_EN.finditer(text)) + list(re.finditer(r"[:：]\s*", text))
    for m in intros:
        rest = text[m.end():]
        for stop in (_SENTENCE_END, _MESSAGE_END):
            end = stop.search(rest)
            out.append(rest[: end.start()] if end else rest)
    out.append(text)
    seen, uniq = set(), []
    for c in out:
        n = normalize_any(c)
        if n and n not in seen:
            seen.add(n)
            uniq.append(c.strip().strip("'‘’\"“”«»").strip())
    return uniq
