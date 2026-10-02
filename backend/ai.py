"""Claude API integration: quote extraction and plain-language explanations.

The model never decides whether a text is authentic. It only:
  1. finds the quoted verse/hadith inside a messy message, and
  2. explains a result that was already computed from the source data.

Both steps are guarded: extracted quotes must appear in the user's message
(so the model cannot invent text), and if the API is unavailable the app
falls back to rule-based extraction and a template explanation.
"""
import json
import os

from arabic import normalize

MODEL = os.environ.get("TABAYYAN_MODEL", "claude-haiku-4-5-20251001")

_client = None


def client():
    global _client
    if _client is None and os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic
        _client = anthropic.Anthropic(timeout=15, max_retries=1)
    return _client


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
            model=MODEL,
            max_tokens=600,
            system=EXTRACT_SYSTEM,
            messages=[{"role": "user", "content": message[:4000]}],
        )
        raw = resp.content[0].text.strip()
        raw = raw[raw.find("{"): raw.rfind("}") + 1]
        quotes = json.loads(raw).get("quotes", [])
    except Exception:
        return None

    # Guard: keep only quotes that really appear in the message.
    msg = normalize(message)
    out = []
    for q in quotes:
        t = str(q.get("text", "")).strip()
        if t and normalize(t) and normalize(t) in msg:
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
            k: result["match"].get(k) for k in ("type", "ref", "grades", "grade_summary")
        },
        "changed_words": [d["word"] for d in (result.get("diff") or []) if d["status"] != "same"],
        "warnings": result.get("warnings", []),
    }
    try:
        resp = c.messages.create(
            model=MODEL,
            max_tokens=300,
            system=EXPLAIN_SYSTEM.format(lang="Arabic" if lang == "ar" else "English"),
            messages=[{"role": "user", "content": json.dumps(facts, ensure_ascii=False)}],
        )
        return resp.content[0].text.strip()
    except Exception:
        return None
