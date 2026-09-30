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


def candidates(text: str) -> list[str]:
    """Possible quote spans, most specific first. Always ends with the full text."""
    out = []
    for m in _QUOTES.finditer(text):
        out.append(m.group(1))
    for m in _INTRO.finditer(text):
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
