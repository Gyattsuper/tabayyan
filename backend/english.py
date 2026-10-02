"""English text normalization for matching quotes against translations.

People share English translations of verses and hadiths with different
punctuation, capitalization, and honorifics ("(ﷺ)", "(pbuh)", "peace be upon
him"). We normalize both sides the same way, as for Arabic.

Words the translator added in brackets or parentheses ("He is Allah, [who is]
One", "worship Me (Alone)") are dropped on both sides: people quote them
inconsistently, and they are not part of the original text.
"""
import re

_INSERTIONS = re.compile(r"\[[^\]]*\]|\([^)]*\)")
_HONORIFICS = re.compile(
    r"ﷺ|peace be upon him|sallallahu alaihi wa ?sallam|"
    r"\bmay allah be pleased with (?:him|her|them|both of them)\b",
    re.IGNORECASE,
)
_APOSTROPHES = re.compile(r"[’'`ʼ‘]")
_NON_WORD = re.compile(r"[^a-z0-9]+")


def normalize_en(text: str) -> str:
    text = _INSERTIONS.sub(" ", text)
    text = _HONORIFICS.sub(" ", text)
    text = _APOSTROPHES.sub("", text.lower())
    return _NON_WORD.sub(" ", text).strip()


# Function words. Two texts sharing only these are not the same text.
STOPWORDS_EN = set(normalize_en(
    "a an the and or but of to in on at by for from with as is are was were be been being it its "
    "this that these those he him his she her they them their we us our you your i me my "
    "not no so if then than there which who whom what when where will would shall should can could "
    "do does did has have had said says say upon unto allah messenger prophet o"
).split())

_LATIN = re.compile(r"[A-Za-z]")
_ARABIC = re.compile(r"[ء-ي]")


def is_english(text: str) -> bool:
    """True when the text is mostly Latin letters (an English quote)."""
    latin, arabic = len(_LATIN.findall(text)), len(_ARABIC.findall(text))
    return latin > arabic


def source_words_en(text: str) -> list[tuple[str, str]]:
    """Words of a translation paired with their normalized form. Words inside
    brackets or parentheses get an empty form, so they are shown but not compared."""
    # Separate words glued to punctuation or insertions: 'Prophet(s.a.w)', 'said:"None'
    text = re.sub(r"([:;,])(?=[\"“'‘\w])", r"\1 ", text)
    text = re.sub(r"(\w)([(\[])", r"\1 \2", text)
    text = re.sub(r"([)\]])(\w)", r"\1 \2", text)
    out, depth = [], 0
    for w in text.split():
        opens, closes = w.count("[") + w.count("("), w.count("]") + w.count(")")
        inside = depth > 0 or opens > 0
        depth = max(0, depth + opens - closes)
        out.append((w, "" if inside else normalize_en(w)))
    return out
