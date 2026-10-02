"""Checks for the features around a check that don't need the AI service:
the guards, the templates, image loading, and alternative retrieval.

Usage:  python tests/run_feature_tests.py
"""
import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import extras  # noqa: E402
from matcher import Matcher  # noqa: E402
from verify import grade_summary, names_unknown_book  # noqa: E402

passed = failed = 0


def check(name, ok):
    global passed, failed
    passed += bool(ok)
    failed += not ok
    print(("PASS  " if ok else "FAIL  ") + name)


m = Matcher()

# Guard against made-up references
check("book guard: rejects a book not in the result", names_unknown_book("رواه مسلم", "صحيح البخاري، رقم 1"))
check("book guard: allows the book in the result", not names_unknown_book("رواه مسلم", "صحيح مسلم، رقم 5"))
check("book guard: 'المسلم' is not the book Muslim", not names_unknown_book("قال المسلم كذا", ""))
check("number guard: rejects a number not in the result", not extras._clean("رقم 99", "صحيح البخاري، رقم 1"))
check("number guard: allows numbers from the link", extras._clean("https://quran.com/51/56", "https://quran.com/51/56"))

# Alternatives only come from strongly graded hadiths and verses
terms = {"en": ["Whoever follows a path seeking knowledge, Allah makes easy for him a path to Paradise"],
         "ar": "طريقا يلتمس فيه علما"}
alts = extras.retrieve(m, terms)
check("alternatives: candidates found", len(alts) > 0)
check("alternatives: all candidates are verses or sahih/hasan hadiths",
      all(r["type"] == "quran" or grade_summary(r["grades"])[1] == "strong" for r in alts))
check("alternatives: no multi-verse runs", all("ayah_end" not in r for r in alts))

# Template replies (used when the AI is unavailable or its reply is rejected)
nf = {"verdict": "not_found", "quote": "اطلبوا العلم ولو في الصين", "claimed": "hadith", "match": None}
r = extras.reply(nf, None, "ar")
check("reply: not found, template, no claim of fabrication", r["source"] == "template" and "مكذوب" not in r["reply"])
part = {"verdict": "partial", "quote": "x", "claimed": "quran",
        "match": {"ref": "سورة الذاريات، آية 56", "link": "https://quran.com/51/56",
                  "words": [{"word": "لِيَعْبُدُونِ", "status": "changed"}]}}
r = extras.reply(part, None, "en")
check("reply: partial includes the correct text and link", "لِيَعْبُدُونِ" in r["reply"] and "quran.com/51/56" in r["reply"])

# Images: the bytes decide the type
png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 100).decode()
check("image: PNG data URL accepted", extras.load_image("data:image/jpeg;base64," + png, None) == (png, "image/png"))
check("image: non-image rejected", extras.load_image(base64.b64encode(b"hello world").decode(), None) is None)
check("image: non-http URL rejected", extras.load_image(None, "file:///etc/passwd") is None)

# Hadith of the day comes from the data
d = extras.daily(m, "ar")
check("daily: from an-Nawawi's Forty, no HTML", "النووية" in d["ref"] and "<br" not in d["text"])

print(f"\n{passed}/{passed + failed} passed")
sys.exit(1 if failed else 0)
