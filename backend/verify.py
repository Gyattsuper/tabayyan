"""Turn a message into verification results the interface can show.

Pipeline: extract quotes (Claude, or rules as fallback) -> match each quote
against the sources -> verdict, reference, correct text, word diff,
gradings, warnings -> explanation.

Results come in Arabic or English (`lang`). Quotes can be in either language:
English quotes are matched against English translations.
"""
import re
from collections import Counter
from difflib import SequenceMatcher
from urllib.parse import quote as urlquote

from rapidfuzz import fuzz

import ai
from arabic import normalize
from english import normalize_en, source_words_en
from extract import candidates, claimed_kind
from matcher import FOUND, Match, Matcher, verdict

STRONG = {"صحيح", "حسن"}
WEAK = {"ضعيف", "موضوع", "منكر", "باطل", "شاذ"}
HONORIFIC_WORDS = set(normalize("صلى الله عليه وسلم رضي عنه عنها عنهما السلام الصلاة").split())

# sunnah.com numbering matches the dataset for these collections (spot-checked).
SUNNAH_DIRECT = {"bukhari": "bukhari", "abudawud": "abudawud", "tirmidhi": "tirmidhi",
                 "nasai": "nasai", "ibnmajah": "ibnmajah", "nawawi": "nawawi40", "qudsi": "qudsi40"}

TEXT = {
    "ar": {
        "scope": "البحث يشمل القرآن الكريم وتسعة من كتب الحديث: الصحيحين والسنن الأربع وموطأ مالك "
                 "والأربعين النووية والأحاديث القدسية.",
        "scope_en": " والنصوص الإنجليزية تُقارن بأربع ترجمات لمعاني القرآن (صحيح إنترناشونال، يوسف علي، "
                    "بكثال، الهلالي وخان) وبترجمة موقع sunnah.com للأحاديث.",
        "no_grade": "لم تُذكر له درجة في المصدر",
        "disputed_label": "مختلف في درجته",
        "w_quran_as_hadith": "هذا النص آية من القرآن الكريم، وليس حديثًا نبويًا كما ورد في الرسالة.",
        "w_athar_is_quran": "هذا النص آية من القرآن الكريم، وليس من كلام من نُسب إليه في الرسالة.",
        "w_hadith_as_quran": "هذا النص ليس آية قرآنية، وإنما ورد في كتب الحديث.",
        "w_weak": "النص موجود في المصدر، لكن العلماء المذكورين حكموا عليه بالضعف، فلا تصح نسبته إلى النبي ﷺ بثقة.",
        "w_disputed": "اختلف العلماء في درجة هذا الحديث، والأحكام معروضة كما وردت.",
        "w_translation": "الكلمات المظللة تختلف عن ترجمة {translator}. قد يكون السبب أن النص من ترجمة أخرى، "
                         "فقارن المعنى بالنص العربي قبل نشره.",
        "w_athar": "الرسالة تنسب هذا القول إلى أحد الصحابة أو العلماء، لا إلى النبي ﷺ. تبيّن يبحث في القرآن "
                   "وكتب الحديث فقط، وكثير من أقوال الصحابة والعلماء مروية في كتب أخرى لا يشملها البحث، "
                   "فعدم وجوده هنا لا يعني أن نسبته خاطئة. للتحقق منه ارجع إلى كتب الآثار وأهل العلم، "
                   "ولا تنسبه إلى النبي ﷺ.",
        "w_not_found": "لم نجد هذا النص في المصادر التي نبحث فيها. هذا وحده لا يعني أنه مكذوب، "
                       "لكن لا تنشره منسوبًا إلى القرآن أو السنة قبل سؤال أهل العلم.",
        "w_not_found_en": "لم نجد هذا النص في الترجمات الإنجليزية التي نبحث فيها. الترجمات تختلف كثيرًا، "
                          "فالتحقق من النص العربي أدق. لا تنشره منسوبًا إلى القرآن أو السنة قبل سؤال أهل العلم.",
        "found": "النص موجود في {ref}.",
        "found_en": "النص يطابق ترجمة {translator} لـ{ref}.",
        "grade": " درجته: {grade}.",
        "partial": "النص قريب مما في {ref}، لكن فيه {count} عن الأصل، وهي مظللة في النص الصحيح. "
                   "انقل النص الصحيح إن أردت نشره.",
        "partial_en": "النص قريب من ترجمة {translator} لـ{ref}، مع اختلاف في {count}.",
        "empty": "لم نجد في النص ما يمكن البحث عنه. الصق نص الآية أو الحديث نفسه، ثلاث كلمات على الأقل.",
    },
    "en": {
        "scope": "Searched: the Quran and nine hadith collections (Bukhari, Muslim, the four Sunan, "
                 "Muwatta Malik, Nawawi's Forty and the Forty Qudsi).",
        "scope_en": " English quotes are compared with four Quran translations (Saheeh International, "
                    "Yusuf Ali, Pickthall, Hilali and Khan) and the sunnah.com hadith translations.",
        "no_grade": "No grading given in the source",
        "disputed_label": "Graded differently by scholars",
        "w_quran_as_hadith": "This is a verse of the Quran, not a hadith as the message says.",
        "w_athar_is_quran": "This is a verse of the Quran, not the words of the person the message names.",
        "w_hadith_as_quran": "This is not a verse of the Quran. It is found in the hadith collections.",
        "w_weak": "This text is in the source, but the scholars listed graded it weak, so it cannot be "
                  "confidently attributed to the Prophet ﷺ.",
        "w_disputed": "Scholars differ on the grading of this hadith. Their gradings are shown as given.",
        "w_translation": "The highlighted words differ from the {translator} translation. This may simply "
                         "be a different translation, so compare the meaning with the Arabic before sharing.",
        "w_athar": "The message attributes this to a companion or a scholar, not to the Prophet ﷺ. Tabayyan "
                   "searches only the Quran and hadith collections, and most sayings of companions and "
                   "scholars are reported in other books, so not finding it here does not mean the "
                   "attribution is wrong. Check it with scholars, and do not attribute it to the Prophet ﷺ.",
        "w_not_found": "We did not find this text in the sources we search. That alone does not mean it is "
                       "fabricated, but do not share it as Quran or hadith before asking a scholar.",
        "w_not_found_en": "We did not find this text in the English translations we search. Translations "
                          "vary a lot, so checking the Arabic text is more reliable. Do not share it as "
                          "Quran or hadith before asking a scholar.",
        "found": "This text is in {ref}.",
        "found_en": "This matches the {translator} translation of {ref}.",
        "grade": " Grading: {grade}.",
        "partial": "This is close to {ref}, but {count} from the source. They are highlighted in the "
                   "correct text. Copy the correct text if you want to share it.",
        "partial_en": "This is close to the {translator} translation of {ref}, with {count}.",
        "empty": "There is nothing here we can search for. Paste the verse or hadith itself, at least three words.",
    },
}


def word_count(n: int, lang: str, english_match: bool = False) -> str:
    if lang == "en":
        if english_match:
            return "1 word different" if n == 1 else f"{n} words different"
        return "1 word differs" if n == 1 else f"{n} words differ"
    return {1: "كلمة واحدة تختلف", 2: "كلمتان تختلفان"}.get(n, f"{n} كلمات تختلف" if n <= 10 else f"{n} كلمة تختلف")


# ---------- presentation helpers ----------

def grade_status(label: str) -> str:
    return "strong" if label in STRONG else "weak" if label in WEAK else "none"


def grade_summary(grades: list[dict], lang: str = "ar") -> tuple[str, str]:
    """(label, status) where status is strong | weak | disputed | none."""
    t = TEXT[lang]
    labels = [g["grade"] for g in grades]  # Arabic labels decide the status
    if not labels:
        return t["no_grade"], "none"
    strong = [l for l in labels if l in STRONG]
    weak = [l for l in labels if l in WEAK]
    if strong and weak:
        return t["disputed_label"], "disputed"
    pick = Counter(weak or strong or labels).most_common(1)[0][0]
    status = "weak" if weak else "strong" if strong else "none"
    if lang == "en":
        pick = next((g.get("grade_en", pick) for g in grades if g["grade"] == pick), pick)
    return pick, status


def localized_grades(grades: list[dict], lang: str) -> list[dict]:
    key_s, key_g = ("scholar_en", "grade_en") if lang == "en" else ("scholar", "grade")
    return [{"scholar": g.get(key_s, g["scholar"]), "grade": g.get(key_g, g["grade"]),
             "status": grade_status(g["grade"])} for g in grades]


def ref_of(r: dict, lang: str) -> str:
    return (r.get("ref_en") or r["ref"]) if lang == "en" else r["ref"]


def link_for(r: dict) -> str:
    if r["type"] == "quran":
        return f"https://quran.com/{r['surah']}/{r['ayah']}"
    if r["book"] in SUNNAH_DIRECT:
        return f"https://sunnah.com/{SUNNAH_DIRECT[r['book']]}:{r['number']}"
    return f"https://sunnah.com/search?q={urlquote(' '.join(r['norm'].split()[:8]))}"


def source_words(text: str) -> list[tuple[str, str]]:
    """Original words paired with their normalized form."""
    return [(w, normalize(w)) for w in text.split()]


def locate_span(words: list[tuple[str, str]], span_norm: str, quote_norm: str) -> tuple[int, int]:
    """Find the matched span inside the original words (with diacritics, or the
    translation as written). Returns [start, end) word indices."""
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
    return keep[first][0], keep[last][0] + 1


def word_diff(quote: str, source_norm_words: list[str], norm=normalize) -> tuple[list[dict], set[int]]:
    """Mark the user's words (as they typed them) as same/changed/extra, and
    return which source word indices were missing or different."""
    typed = [(w, norm(w)) for w in quote.split()]
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
    t = TEXT[lang]
    v = verdict(matches)
    res = {"verdict": v, "quote": quote, "claimed": claimed, "match": None,
           "diff": None, "others": [], "warnings": [], "lang": lang}
    english_quote = bool(matches) and matches[0].english

    if v != "not_found":
        m = matches[0]
        r = m.record
        if m.english:
            words, norm = source_words_en(r["en_text"]), normalize_en
        else:
            words, norm = source_words(r["text"]), normalize
        a, b = locate_span(words, m.span, norm(quote))
        # compare only real words (skip punctuation and translator insertions), remembering their positions
        real = [k for k in range(a, b) if words[k][1]]
        diff, changed_idx = word_diff(quote, [words[k][1] for k in real], norm)
        changed = {real[i] for i in changed_idx}
        # Mark the source span word by word so the interface can highlight differences.
        highlighted = []
        for k, (w, n) in enumerate(words):
            status = "context"
            if a <= k < b:
                status = "changed" if k in changed and n and n not in HONORIFIC_WORDS else "match"
            highlighted.append({"word": w, "status": status})
        label, status = grade_summary(r.get("grades", []), lang)
        res["match"] = {
            "type": r["type"],
            "ref": ref_of(r, lang),
            "words": highlighted,
            "words_lang": "en" if m.english else "ar",
            "translator": r.get("translator") if m.english else None,
            "arabic": r["text"] if m.english else None,
            "english": "" if m.english else r.get("english", ""),
            "grades": localized_grades(r.get("grades", []), lang),
            "grade_summary": label if r["type"] == "hadith" else None,
            "grade_status": status if r["type"] == "hadith" else None,
            "link": link_for(r),
        }
        res["diff"] = diff
        res["n_diff"] = max(sum(d["status"] != "same" for d in diff), len(changed))
        # Other places the same text appears
        seen = {r["ref"]}
        for o in matches[1:]:
            if (o.score >= FOUND and o.coverage == 1.0 and o.record["type"] == r["type"]
                    and o.record["ref"] not in seen and "ayah_end" not in o.record):
                seen.add(o.record["ref"])
                res["others"].append({"ref": ref_of(o.record, lang), "link": link_for(o.record)})

        if claimed == "hadith" and r["type"] == "quran":
            res["warnings"].append(t["w_quran_as_hadith"])
        if claimed == "athar" and r["type"] == "quran":
            res["warnings"].append(t["w_athar_is_quran"])
        if claimed == "quran" and r["type"] == "hadith":
            res["warnings"].append(t["w_hadith_as_quran"])
        if r["type"] == "hadith" and status == "weak":
            res["warnings"].append(t["w_weak"])
        if r["type"] == "hadith" and status == "disputed":
            res["warnings"].append(t["w_disputed"])
        if m.english and v == "partial":
            res["warnings"].append(t["w_translation"].format(translator=r["translator"]))
    elif claimed == "athar":
        # A companion's or scholar's saying: many are reported in books we don't index,
        # so "not found" here says nothing about whether the attribution is right.
        res["warnings"].append(t["w_athar"])
    else:
        res["warnings"].append(t["w_not_found_en"] if english_quote or _looks_english(quote) else t["w_not_found"])
    res["quote_lang"] = "en" if english_quote or (v == "not_found" and _looks_english(quote)) else "ar"
    res["scope"] = t["scope"] + (t["scope_en"] if res["quote_lang"] == "en" else "")
    expl = ai.explain(res, lang)
    res["explanation_source"] = "claude" if expl and explanation_is_grounded(expl, res, matches) else "template"
    res["explanation"] = expl if res["explanation_source"] == "claude" else template_explanation(res)
    return res


def _looks_english(text: str) -> bool:
    from english import is_english
    return is_english(text)


BOOK_NAMES = ["البخاري", "مسلم", "أبي داود", "أبو داود", "الترمذي", "النسائي", "ابن ماجه", "مالك", "الموطأ",
              "النووية", "القدسية", "أحمد", "المسند", "البيهقي", "الطبراني", "الحاكم", "Bukhari", "Muslim",
              "Dawud", "Tirmidhi", "Nasa", "Majah", "Malik", "Nawawi", "Ahmad", "Bayhaqi", "Tabarani", "Hakim"]


def explanation_is_grounded(expl: str, res: dict, matches: list[Match] | None = None) -> bool:
    """Reject a model explanation that names a book or number not in the result."""
    refs = []
    if res["match"]:
        recs = [m.record for m in (matches or [])[:1]]
        refs = [res["match"]["ref"]] + [o["ref"] for o in res["others"]]
        refs += [r.get("ref") or "" for r in recs] + [r.get("ref_en") or "" for r in recs]
    allowed = " ".join(refs)
    allowed_n = normalize(allowed)
    for name in BOOK_NAMES:
        n = normalize(name) or name.lower()
        if (n in normalize(expl) or name.lower() in expl.lower()) and n not in allowed_n and name not in allowed:
            return False
    for num in re.findall(r"\d+", expl.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))):
        if num not in re.findall(r"\d+", allowed):
            return False
    return True


def template_explanation(res: dict) -> str:
    t = TEXT[res["lang"]]
    m = res["match"]
    if res["verdict"] == "found":
        base = (t["found_en"].format(translator=m["translator"], ref=m["ref"]) if m["translator"]
                else t["found"].format(ref=m["ref"]))
        if m["type"] == "hadith":
            base += t["grade"].format(grade=m["grade_summary"])
        return base
    if res["verdict"] == "partial":
        n = res.get("n_diff") or 1
        if m["translator"]:
            return t["partial_en"].format(translator=m["translator"], ref=m["ref"],
                                          count=word_count(n, res["lang"], english_match=True))
        return t["partial"].format(ref=m["ref"], count=word_count(n, res["lang"]))
    return ""  # the not-found warning already says everything


_RANK = {"found": 2, "partial": 1, "not_found": 0}


def verify(matcher: Matcher, message: str, lang: str = "ar") -> dict:
    lang = "en" if lang == "en" else "ar"
    message = message.strip()[:4000]
    extracted = ai.extract_quotes(message)
    extractor = "claude" if extracted is not None else "rules"

    def strongest(text):
        best = None
        for cand in candidates(text):
            ms = matcher.search(cand)
            # strongest verdict, then closest match, then the longest quote (the whole verse
            # rather than a piece of it that also happens to match)
            key = (_RANK[verdict(ms)], round(ms[0].score) if ms else 0, len(cand.split()))
            if best is None or key > best[0]:
                best = (key, cand, ms)
        return best

    results = []
    if extracted:
        for q in extracted[:3]:
            best = strongest(q["text"])
            if best is None:
                continue
            claimed = q["claimed"] or claimed_kind(message)
            results.append(build_result(best[1], claimed, best[2], lang))

    if not results:
        # Rule-based: try each candidate span, keep the strongest.
        best = strongest(message)
        if best is not None and max(len(normalize(best[1]).split()), len(normalize_en(best[1]).split())) >= 3:
            results.append(build_result(best[1], claimed_kind(message), best[2], lang))

    out = {"extractor": extractor, "results": results, "lang": lang}
    if not results:
        out["message"] = TEXT[lang]["empty"]
    return out
