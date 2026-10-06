"""Find where a quoted verse or hadith appears in the corpus.

Stage 1 (recall): character n-gram TF-IDF narrows ~42k texts to a few
dozen candidates. Character n-grams tolerate small spelling differences
that word-level search would miss.

Stage 2 (precision): for each candidate, align the quote to the most
similar span of its text. That span is what we show as the "correct text",
and its similarity decides the verdict.

English quotes are matched the same way against English translations (four
of the Quran, one of the hadiths), with a word-level index for stage 1.

Memory: the index is built ahead of time by build_index.py. At runtime only
the sparse index sits in memory; texts are read from SQLite for the few
candidates of each query, which keeps the server within free hosting limits.
"""
import json
import pickle
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from difflib import SequenceMatcher

import numpy as np
from rapidfuzz import fuzz
from scipy import sparse

from arabic import normalize
from english import STOPWORDS_EN, is_english, normalize_en

DATA = Path(__file__).resolve().parent.parent / "data"

FOUND = 90      # near-identical wording
PARTIAL = 70    # same text, noticeably different wording
MIN_WORDS = 3   # quotes shorter than this are too ambiguous to judge
MIN_COVERAGE = 0.6  # share of the quote's content words that must appear in the source
MIN_RUN = 4         # a run of at least 4 words copied exactly from the source...
RUN_SHARE = 0.6     # ...making up most of the quote
MIN_SHARED = 3      # and at least this many of them, so a 3-word saying sharing 2 common words isn't "partial"

# Particles and filler words. Two texts sharing only these are not the same text.
STOPWORDS = set(normalize(
    "من في على الى إلى عن مع ما لا لم لن ان إن أن كان كانت هو هي هم انت قال قالت "
    "و او أو ثم الا إلا انما إنما قد هذا هذه ذلك التي الذي يا به بها له لها فيه منه كل "
    "الله الايمان الإيمان رسول النبي"
).split())


def content_words(text: str, stop: set = STOPWORDS) -> list[str]:
    return [w for w in text.split() if w not in stop and len(w) > 1]


def coverage(q: str, span: str, stop: set = STOPWORDS) -> float:
    """Share of the quote's content words found exactly in the matched span."""
    qw = content_words(q, stop)
    return shared_words(q, span, stop) / len(qw) if qw else 0.0


def shared_words(q: str, span: str, stop: set = STOPWORDS) -> int:
    sw = set(span.split())
    return sum(w in sw for w in content_words(q, stop))


@dataclass
class Match:
    record: dict
    score: float           # 0-100, how close the quote is to the best span
    span: str = ""         # the matching span in the source (normalized words)
    coverage: float = 0.0  # share of the quote's content words present in the span
    exact: bool = False    # every word of the quote matches the source in order, nothing changed or skipped
    shared: int = 0        # number of the quote's content words present in the span
    english: bool = False  # matched against an English translation (record has translator, en_text, en_norm)
    run: int = 0           # longest run of consecutive quote words found word for word in the span
    qlen: int = 0          # words in the quote


def longest_run(q: str, span: str) -> int:
    """Longest run of consecutive words shared, in order, by the quote and the span."""
    a, b = q.split(), span.split()
    best, prev = 0, [0] * (len(b) + 1)
    for x in a:
        cur = [0] * (len(b) + 1)
        for j, y in enumerate(b, 1):
            if x == y:
                cur[j] = prev[j - 1] + 1
                best = max(best, cur[j])
        prev = cur
    return best


def is_exact(q: str, span: str) -> bool:
    """True when the quote is a contiguous, word-for-word piece of the span.

    The span may have extra words before or after the quote (quoting part of a
    verse is fine), but no word may be changed, added, or dropped inside it.
    """
    qw, sw = q.split(), span.split()
    ops = SequenceMatcher(a=qw, b=sw, autojunk=False).get_opcodes()
    eq = [i for i, o in enumerate(ops) if o[0] == "equal"]
    if not eq:
        return False
    for i, (tag, *_rest) in enumerate(ops):
        if tag == "equal":
            continue
        if tag == "insert" and (i < eq[0] or i > eq[-1]):
            continue  # source words before/after the quoted part
        return False
    return True


# When the same text appears in several places, cite the strongest source first.
BOOK_PRIORITY = ["bukhari", "muslim", "abudawud", "tirmidhi", "nasai", "ibnmajah", "malik", "nawawi", "qudsi"]
TRANSLATOR_PRIORITY = ["Saheeh International", "Yusuf Ali", "Pickthall", "Hilali and Khan", "sunnah.com"]


def _rank_key(m: "Match"):
    r = m.record
    if r["type"] == "quran":
        # the Quran itself beats a hadith quoting it; a single verse beats a run containing it
        source = (2, -len(r["norm"]))
    else:
        source = (1, -BOOK_PRIORITY.index(r["book"]))
    translator = -TRANSLATOR_PRIORITY.index(r["translator"]) if m.english else 0
    return (m.exact, round(m.score), m.coverage, source, translator)


class Matcher:
    def __init__(self, data_dir: Path = DATA):
        with open(data_dir / "vectorizer.pkl", "rb") as f:
            self.vec = pickle.load(f)
        self.matrix = sparse.load_npz(data_dir / "tfidf.npz").tocsr()
        self.types = np.load(data_dir / "types.npy")  # 0 = quran, 1 = hadith
        self.count = self.matrix.shape[0]
        self.db = sqlite3.connect(data_dir / "corpus.db", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with open(data_dir / "en_vectorizer.pkl", "rb") as f:
            self.en_vec = pickle.load(f)
        self.en_matrix = sparse.load_npz(data_dir / "en_tfidf.npz").tocsr()
        self.en_types = np.load(data_dir / "en_types.npy")

    @staticmethod
    def _row(row) -> dict:
        r = dict(row)
        r["grades"] = json.loads(r["grades"] or "[]")
        if r["ayah_end"] is None:
            del r["ayah_end"]
        return r

    def fetch(self, ids: list[int]) -> dict[int, dict]:
        rows = self.db.execute(
            f"SELECT * FROM records WHERE id IN ({','.join('?' * len(ids))})", [int(i) for i in ids]
        ).fetchall()
        return {r["id"]: r for r in map(self._row, rows)}

    def fetch_en(self, ids: list[int]) -> dict[int, dict]:
        """English translation rows, each joined with the Arabic record it translates."""
        rows = self.db.execute(
            f"SELECT e.id AS en_id, e.translator, e.en_text, e.en_norm, r.* FROM en_records e "
            f"JOIN records r ON r.id = e.record_id WHERE e.id IN ({','.join('?' * len(ids))})", [int(i) for i in ids]
        ).fetchall()
        return {r["en_id"]: r for r in map(self._row, rows)}

    @staticmethod
    def _best_span(q: str, doc: str) -> tuple[float, str]:
        """Best-matching substring of doc, snapped to whole words."""
        if len(doc) <= len(q):
            return fuzz.ratio(q, doc), doc
        a = fuzz.partial_ratio_alignment(q, doc)
        start, end = a.dest_start, a.dest_end
        while start > 0 and doc[start - 1] != " ":
            start -= 1
        while end < len(doc) and doc[end] != " ":
            end += 1
        span = doc[start:end].strip()
        # Re-score on the snapped span so partial words don't inflate the score
        score = fuzz.ratio(q, span)
        # A short text (one verse) can be a better match as a whole than any window of it,
        # e.g. when the quote changed a word at the very end.
        if len(doc) <= 1.5 * len(q):
            whole = fuzz.ratio(q, doc)
            if whole > score:
                return whole, doc
        return score, span

    def search(self, text: str, kind: str | None = None, k: int = 40, top: int = 3) -> list[Match]:
        english = is_english(text)
        if english:
            q, vec, matrix, types, fetch, field, stop = (normalize_en(text), self.en_vec, self.en_matrix,
                                                         self.en_types, self.fetch_en, "en_norm", STOPWORDS_EN)
        else:
            q, vec, matrix, types, fetch, field, stop = (normalize(text), self.vec, self.matrix,
                                                         self.types, self.fetch, "norm", STOPWORDS)
        if len(q.split()) < MIN_WORDS:
            return []
        sims = (matrix @ vec.transform([q]).T).toarray().ravel()
        if kind:
            sims[types != (0 if kind == "quran" else 1)] = -1
        # English: each verse is indexed in four translations and in runs of verses, and long
        # hadith translations score lower in a word index, so look at more candidates.
        k = min(k * (10 if english else 1), len(sims) - 1)
        cands = np.argpartition(-sims, k)[:k]
        records = fetch(list(cands))
        results = []
        for i in cands:
            r = records[int(i)]
            score, span = self._best_span(q, r[field])
            if score >= PARTIAL - 15:
                results.append(Match(r, score, span, coverage(q, span, stop), is_exact(q, span),
                                     shared_words(q, span, stop), english, longest_run(q, span), len(q.split())))
        results.sort(key=_rank_key, reverse=True)
        # The same verse can match through several translations; keep its best one.
        seen, out = set(), []
        for m in results:
            if m.record["id"] not in seen:
                seen.add(m.record["id"])
                out.append(m)
        return out[:top]


def verdict(matches: list[Match]) -> str:
    if not matches:
        return "not_found"
    m = matches[0]
    # "found" means every meaningful word matches exactly. A single changed word
    # in a verse or hadith must never pass as correct.
    if m.exact and m.coverage == 1.0:
        return "found"
    if m.score >= PARTIAL and m.coverage >= MIN_COVERAGE and m.shared >= MIN_SHARED:
        return "partial"
    # A short verse or hadith with words added to it («إن الله مع الصابرين والمحسنين»): most of the
    # quote is the source word for word, so show the correct text, even though few of its words
    # are distinctive enough to count above.
    if (not m.english and m.score >= PARTIAL and m.run >= MIN_RUN and m.run >= RUN_SHARE * m.qlen):
        return "partial"
    return "not_found"


_RANK = {"found": 2, "partial": 1, "not_found": 0}


def check(matcher: Matcher, text: str) -> tuple[str, list[Match], str]:
    """Try each candidate quote in the message and keep the strongest result.

    Returns (verdict, matches, the quote that was checked).
    """
    from extract import candidates

    best = ("not_found", [], text)
    for quote in candidates(text):
        matches = matcher.search(quote)
        v = verdict(matches)
        cur = (_RANK[v], matches[0].score if matches else 0)
        prev = (_RANK[best[0]], best[1][0].score if best[1] else 0)
        if cur > prev:
            best = (v, matches, quote)
        if v == "found":
            break
    return best
