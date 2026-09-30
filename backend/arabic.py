"""Arabic text normalization for matching.

Quotes shared on social media rarely match the source letter for letter:
diacritics are dropped or added, alef forms vary, taa marbuta is written
as haa, and so on. We normalize both the sources and the user's text the
same way before comparing them.
"""
import re

# Harakat, tanween, shadda, sukun, dagger alef, Quranic annotation marks
_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ࣓-ࣿ]")
_TATWEEL = "ـ"
_NON_ARABIC = re.compile(r"[^ء-ي\s]")
_SPACES = re.compile(r"\s+")

_LETTER_MAP = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ٲ": "ا", "ٳ": "ا",
    "ى": "ي", "ی": "ي", "ئ": "ي",
    "ؤ": "و",
    "ة": "ه",
    "ک": "ك",
})

# Honorifics that people add or drop freely; they shouldn't affect matching.
_HONORIFICS = re.compile(
    r"صلى الله عليه وسلم|صلي الله عليه وسلم|عليه الصلاه والسلام|عليه السلام|رضي الله عنهما|رضي الله عنها|رضي الله عنه"
)


def normalize(text: str) -> str:
    text = text.replace("ﷺ", " ")
    text = _DIACRITICS.sub("", text).replace(_TATWEEL, "")
    text = text.translate(_LETTER_MAP)
    text = _NON_ARABIC.sub(" ", text)
    text = _HONORIFICS.sub(" ", text)
    return _SPACES.sub(" ", text).strip()


def words(text: str) -> list[str]:
    return normalize(text).split()
