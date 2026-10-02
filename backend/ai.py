"""Claude API integration.

The model never decides whether a text is authentic. It only:
  1. finds the quoted verse/hadith inside a messy message (or reads it from an image),
  2. explains a result that was already computed from the source data,
  3. picks related authentic texts from candidates we retrieved from the sources, and
  4. drafts a polite reply from the computed facts.

Each step is guarded: extracted quotes must appear in the user's message, picked
alternatives must be among our candidates and quote their text exactly, and text
naming a book or number not in the result is rejected. If the API is unavailable
the app falls back to rules and templates (image reading and alternatives need it).
"""
import json
import logging
import os

log = logging.getLogger("tabayyan.ai")

from arabic import normalize
from english import normalize_en


def _appears(quote: str, message: str) -> bool:
    """The quote occurs in the message (after normalization, in either script)."""
    for norm in (normalize, normalize_en):
        q = norm(quote)
        if q and q in norm(message):
            return True
    return False

MODEL = os.environ.get("TABAYYAN_MODEL", "claude-sonnet-5-5")

_client = None


def client():
    global _client
    if _client is None and os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic
        _client = anthropic.Anthropic(timeout=15, max_retries=1)
    return _client


def _text(resp) -> str:
    """The reply text. Newer models may return thinking blocks before it, so skip those."""
    return "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")


def enabled() -> bool:
    return client() is not None


EXTRACT_SYSTEM = """You extract quoted Quran verses and hadith texts from messages people share.

Return JSON only, in this exact shape:
{"quotes": [{"text": "...", "claimed": "hadith" | "quran" | "other" | "unknown"}]}

Rules:
- Copy each quote exactly as it appears in the message. Never correct, complete, or add words.
- Leave out introductions ("قال رسول الله ﷺ:", "قال تعالى:"), honorifics, and surrounding commentary.
- "claimed" is what the message says the text is, not what you think it is. Use "other" when the
  message attributes it to a companion, a scholar, or anyone other than the Prophet ﷺ or Allah.
- If there is no quote, return {"quotes": []}.
- If the whole message is the quote, return it whole."""


def extract_quotes(message: str) -> list[dict] | None:
    """Returns [{'text', 'claimed'}], or None if the API is unavailable or failed."""
    c = client()
    if c is None:
        return None
    try:
        resp = c.messages.create(
            thinking={"type": "disabled"},  # short, focused tasks: answer directly
            model=MODEL,
            max_tokens=600,
            system=EXTRACT_SYSTEM,
            messages=[{"role": "user", "content": message[:4000]}],
        )
        raw = _text(resp).strip()
        raw = raw[raw.find("{"): raw.rfind("}") + 1]
        quotes = json.loads(raw).get("quotes", [])
    except Exception:
        log.exception("Claude call failed")
        return None

    # Guard: keep only quotes that really appear in the message.
    out = []
    for q in quotes:
        t = str(q.get("text", "")).strip()
        if t and _appears(t, message):
            claimed = q.get("claimed")
            claimed = {"hadith": "hadith", "quran": "quran", "other": "athar"}.get(claimed)
            out.append({"text": t, "claimed": claimed})
    return out


EXPLAIN_SYSTEM = """You write a short explanation of a verification result for a general reader.

You receive a JSON result computed from authenticated sources. Explain it in 2 to 3 plain sentences in {lang}.

Rules:
- Use ONLY the facts in the JSON. Never add references, gradings, narrators, or meanings that are not in it.
- Never issue a religious ruling or say what someone should believe or do religiously.
- For "not_found": say the text was not found in the searched collections, that this alone does not prove it is fabricated, and suggest asking a qualified scholar before sharing it.
- For "partial": point out which words differ from the source.
- If gradings differ between scholars, say so without choosing between them.
- If "claimed_as" is "athar", the message attributes the text to a companion or scholar, not the Prophet.
  If it was not found, say only that the searched sources are the Quran and hadith books, that such
  sayings are often reported elsewhere, and that this result does not judge the attribution.
- If the only grading's "scholar" is the collection itself (صحيح البخاري or صحيح مسلم), do not say a person graded it. Say it is in that Sahih, whose hadiths are accepted as authentic.
- Do not use digits except the reference number exactly as given.
- If "translator" is set, the quote was compared with that English translation. A partial match may
  just be a different translation, so say that instead of calling the quote altered.
- No greetings, no markdown."""


def explain(result: dict, lang: str = "ar") -> str | None:
    c = client()
    if c is None:
        return None
    facts = {
        "verdict": result["verdict"],
        "checked_text": result["quote"],
        "claimed_as": result.get("claimed"),
        "source": result.get("match") and {
            k: result["match"].get(k) for k in ("type", "ref", "translator", "grades", "grade_summary")
        },
        "quote_language": result.get("quote_lang"),
        "changed_words": [d["word"] for d in (result.get("diff") or []) if d["status"] != "same"],
        "warnings": result.get("warnings", []),
    }
    try:
        resp = c.messages.create(
            thinking={"type": "disabled"},  # short, focused tasks: answer directly
            model=MODEL,
            max_tokens=300,
            system=EXPLAIN_SYSTEM.format(lang="Arabic" if lang == "ar" else "English"),
            messages=[{"role": "user", "content": json.dumps(facts, ensure_ascii=False)}],
        )
        return _text(resp).strip()
    except Exception:
        log.exception("Claude call failed")
        return None


# ---------- reading text from images ----------

TRANSCRIBE_SYSTEM = """You transcribe the text in an image (a screenshot, a social media post, a designed card).

Rules:
- Copy the text exactly as written, line by line, in its original language.
- Never correct, complete, or "fix" anything. If a verse or hadith looks misquoted, keep it exactly as
  it appears in the image. People use this to check whether the image is accurate, so a correction would
  hide the error.
- Keep diacritics if they are in the image. Do not add any.
- Skip only interface clutter (timestamps, like counts, app buttons).
- Output only the transcribed text. If there is no readable text, output nothing."""


def transcribe_image(b64: str, media_type: str) -> str | None:
    c = client()
    if c is None:
        return None
    try:
        resp = c.messages.create(
            thinking={"type": "disabled"},  # short, focused tasks: answer directly
            model=MODEL,
            max_tokens=1500,
            system=TRANSCRIBE_SYSTEM,
            timeout=45,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": "Transcribe the text in this image."},
            ]}],
        )
        return _text(resp).strip()
    except Exception:
        log.exception("Claude call failed")
        return None


# ---------- authentic alternatives ----------

SEARCH_TERMS_SYSTEM = """A user checked a saying that was not found in the Quran and hadith collections, or was graded weak.
We will search authenticated sources for verses and hadiths with a related meaning.

Return JSON only: {"en": ["...", "...", "..."], "ar": "..."}
- "en": three different short phrasings of the core meaning in plain English, worded the way English
  translations of hadiths and of the Quran usually word such a meaning (each under 20 words).
- "ar": 4 to 8 Arabic keywords for the core meaning, as they would appear in classical texts.
Your phrasings are only used as search queries. Do not attribute anything to the Prophet ﷺ."""

PICK_SYSTEM = """A user checked a saying that was not found in the sources, or was graded weak. Below it are
candidate texts retrieved from authenticated sources (each with an id).

Pick at most 2 candidates whose meaning is genuinely close to the saying, so the user can share an
authentic text instead. If none is close, pick none.

Return JSON only: {{"picks": [{{"id": 0, "excerpt": "...", "why": "..."}}]}}
- "excerpt": copy, exactly and without changes, the shortest part of the candidate's ARABIC text that carries
  the related meaning (the Prophet's words, not the chain of narrators).
- "why": one short sentence in {lang} on how its meaning relates to the saying. No references, numbers or book names.
- Never issue a ruling. Never claim the saying itself is authentic."""


def _json(raw: str) -> dict:
    raw = raw[raw.find("{"): raw.rfind("}") + 1]
    return json.loads(raw)


def search_terms(text: str) -> dict | None:
    c = client()
    if c is None:
        return None
    try:
        resp = c.messages.create(
            thinking={"type": "disabled"},  # short, focused tasks: answer directlymodel=MODEL, max_tokens=300, system=SEARCH_TERMS_SYSTEM,
                                 messages=[{"role": "user", "content": text[:1000]}])
        d = _json(_text(resp))
        en = d.get("en", [])
        en = [str(x) for x in (en if isinstance(en, list) else [en]) if str(x).strip()][:4]
        return {"en": en, "ar": str(d.get("ar", ""))}
    except Exception:
        log.exception("Claude call failed")
        return None


def pick_alternatives(text: str, candidates: list[dict], lang: str) -> list[dict] | None:
    """candidates: [{'id', 'ref', 'arabic', 'english'}]. Returns [{'id', 'excerpt', 'why'}]."""
    c = client()
    if c is None:
        return None
    listing = "\n\n".join(
        f"[{x['id']}] {x['ref']}\nArabic: {x['arabic'][:900]}\nEnglish: {x['english'][:500]}" for x in candidates)
    try:
        resp = c.messages.create(
            thinking={"type": "disabled"},  # short, focused tasks: answer directly
            model=MODEL, max_tokens=700,
            system=PICK_SYSTEM.format(lang="Arabic" if lang == "ar" else "English"),
            messages=[{"role": "user", "content": f"Saying:\n{text[:1000]}\n\nCandidates:\n{listing}"}])
        return [p for p in _json(_text(resp)).get("picks", []) if isinstance(p, dict)]
    except Exception:
        log.exception("Claude call failed")
        return None


# ---------- polite reply ----------

REPLY_SYSTEM = """Write a short, kind reply that a person can send back to the group or person who shared a
religious message, based on a verification result. Write it in {lang}, 2 to 4 sentences, warm and respectful,
never accusing or preachy, the way a polite friend would write on WhatsApp.

Rules:
- Use ONLY the facts in the JSON. Never add references, gradings, or texts that are not in it.
- If an authentic alternative is given, you may suggest sharing it instead, quoting its excerpt exactly.
- End with the source link if one is given, on its own line.
- Never issue a ruling. For "not found", say it was not found in the main hadith collections and that it is
  better not to attribute it to the Prophet ﷺ without a known source; do not call it a lie.
- Do not use digits except inside the reference exactly as given and the link.
- No markdown, no hashtags, at most one emoji."""


def write_reply(facts: dict, lang: str) -> str | None:
    c = client()
    if c is None:
        return None
    try:
        resp = c.messages.create(
            thinking={"type": "disabled"},  # short, focused tasks: answer directly
            model=MODEL, max_tokens=400,
            system=REPLY_SYSTEM.format(lang="Arabic" if lang == "ar" else "English"),
            messages=[{"role": "user", "content": json.dumps(facts, ensure_ascii=False)}])
        return _text(resp).strip()
    except Exception:
        log.exception("Claude call failed")
        return None
