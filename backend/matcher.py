"""Find where a quoted verse or hadith appears in the corpus.

Stage 1 (recall): character n-gram TF-IDF narrows ~42k texts to a few
dozen candidates. Character n-grams tolerate small spelling differences
that word-level search would miss.

Stage 2 (precision): for each candidate, align the quote to the most
similar span of its text. That span is what we show as the "correct text",
and its similarity decides the verdict.

Memory: the index is built ahead of time by build_index.py. At runtime only
the sparse index sits in memory; texts are read from SQLite for the few
candidates of each query, which keeps the server within free hosting limits.
"""
import json
import pickle
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from rapidfuzz import fuzz
from scipy import sparse

from arabic import normalize

DATA = Path(__file__).resolve().parent.parent / "data"

FOUND = 90      # near-identical wording
PARTIAL = 70    # same text, noticeably different wording
MIN_WORDS = 3   # quotes shorter than this are too ambiguous to judge
MIN_COVERAGE = 0.6  # share of the quote's content words that must appear in the source

# Particles and filler words. Two texts sharing only these are not the same text.
STOPWORDS = set(normalize(
    "من في على الى إلى عن مع ما لا لم لن ان إن أن كان كانت هو هي هم انت قال قالت "
    "و او أو ثم الا إلا انما إنما قد هذا هذه ذلك التي الذي يا به بها له لها فيه منه كل "
    "الله الايمان الإيمان رسول النبي"
).split())


def content_words(text: str) -> list[str]:
    return [w for w in text.split() if w not in STOPWORDS and len(w) > 1]


def coverage(q: str, span: str) -> float:
    """Share of the quote's content words found exactly in the matched span."""
    qw = content_words(q)
    if not qw:
        return 0.0
    sw = set(span.split())
    return sum(w in sw for w in qw) / len(qw)


@dataclass
class Match:
    record: dict
    score: float           # 0-100, how close the quote is to the best span
    span: str = ""         # the matching span in the source (normalized words)
    coverage: float = 0.0  # share of the quote's content words present in the span


# When the same text appears in several places, cite the strongest source first.
BOOK_PRIORITY = ["bukhari", "muslim", "abudawud", "tirmidhi", "nasai", "ibnmajah", "malik", "nawawi", "qudsi"]


def _rank_key(m: "Match"):
    r = m.record
    if r["type"] == "quran":
        # the Quran itself beats a hadith quoting it; a single verse beats a run containing it
        source = (2, -len(r["norm"]))
    else:
        source = (1, -BOOK_PRIORITY.index(r["book"]))
    return (round(m.score), m.coverage, source)


class Matcher:
    def __init__(self, data_dir: Path = DATA):
        with open(data_dir / "vectorizer.pkl", "rb") as f:
            self.vec = pickle.load(f)
        self.matrix = sparse.load_npz(data_dir / "tfidf.npz").tocsr()
        self.types = np.load(data_dir / "types.npy")  # 0 = quran, 1 = hadith
        self.count = self.matrix.shape[0]
        self.db = sqlite3.connect(data_dir / "corpus.db", check_same_thread=False)
        self.db.row_factory = sqlite3.Row

    def fetch(self, ids: list[int]) -> dict[int, dict]:
        rows = self.db.execute(
            f"SELECT * FROM records WHERE id IN ({','.join('?' * len(ids))})", [int(i) for i in ids]
        ).fetchall()
        out = {}
        for row in rows:
            r = dict(row)
            r["grades"] = json.loads(r["grades"] or "[]")
            if r["ayah_end"] is None:
                del r["ayah_end"]
            out[r["id"]] = r
        return out

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
        return fuzz.ratio(q, span), span

    def search(self, text: str, kind: str | None = None, k: int = 40, top: int = 3) -> list[Match]:
        q = normalize(text)
        q_words = q.split()
        if len(q_words) < MIN_WORDS:
            return []
        sims = (self.matrix @ self.vec.transform([q]).T).toarray().ravel()
        if kind:
            sims[self.types != (0 if kind == "quran" else 1)] = -1
        cands = np.argpartition(-sims, k)[:k]
        records = self.fetch(list(cands))
        results = []
        for i in cands:
            r = records[int(i)]
            score, span = self._best_span(q, r["norm"])
            if score >= PARTIAL - 15:
                results.append(Match(r, score, span, coverage(q, span)))
        results.sort(key=_rank_key, reverse=True)
        return results[:top]


def verdict(matches: list[Match]) -> str:
    if not matches:
        return "not_found"
    m = matches[0]
    # "found" means every meaningful word matches exactly. A single changed word
    # in a verse or hadith must never pass as correct.
    if m.score >= FOUND and m.coverage == 1.0:
        return "found"
    if m.score >= PARTIAL and m.coverage >= MIN_COVERAGE:
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
