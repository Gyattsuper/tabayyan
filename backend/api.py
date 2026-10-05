"""Tabayyan HTTP API.

  POST /api/check         {"text": "...", "lang": "ar" | "en"}  -> verification results
  POST /api/check-image   {"image": "data:image/...;base64,..." | "image_url": "https://...", "lang"}
                          -> the text read from the image, then the same results as /api/check
  POST /api/alternatives  {"text": "...", "lang"}  -> authentic texts with a related meaning
  POST /api/reply         {"result": {...}, "alternative": {...} | null, "lang"}  -> a polite reply to send
  GET  /api/daily?lang=   -> hadith of the day (from an-Nawawi's Forty)
  GET  /api/dorar?q=      -> scholars' rulings from the Dorar al-Saniyyah encyclopedia, for texts not in
                             the nine collections
  GET  /api/search?q=&lang=&kind=quran|hadith&all=0|1  -> verses and hadiths matching a topic
  GET  /api/health

Run locally:  uvicorn api:app --port 8000
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import ai
import dorar
import extras
from matcher import Matcher
from verify import verify

app = FastAPI(title="Tabayyan API")
# The web app and the Chrome extension call this API from other origins.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])

matcher = Matcher()


class CheckRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    lang: str = "ar"


@app.get("/api/health")
def health():
    return {"ok": True, "records": matcher.count, "claude": ai.enabled()}


def _lang(lang: str) -> str:
    return "en" if lang == "en" else "ar"


@app.post("/api/check")
def check(req: CheckRequest):
    if not req.text.strip():
        raise HTTPException(400, "empty text")
    return verify(matcher, req.text, _lang(req.lang))


class ImageRequest(BaseModel):
    image: str | None = Field(default=None, max_length=12_000_000)
    image_url: str | None = Field(default=None, max_length=2000)
    lang: str = "ar"


@app.post("/api/check-image")
def check_image(req: ImageRequest):
    lang = _lang(req.lang)
    t = extras.TEXT[lang]
    if not ai.enabled():
        raise HTTPException(503, t["no_ai"])
    try:
        img = extras.load_image(req.image, req.image_url)
    except Exception:
        img = None
    if img is None:
        raise HTTPException(400, t["bad_image"])
    transcript = ai.transcribe_image(*img)
    if transcript is None:
        raise HTTPException(503, t["no_ai"])
    if not transcript.strip():
        return {"transcript": "", "results": [], "lang": lang, "message": t["no_text"]}
    out = verify(matcher, transcript[:4000], lang)
    out["transcript"] = transcript
    return out


class AltRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    lang: str = "ar"


@app.post("/api/alternatives")
def alternatives(req: AltRequest):
    return extras.alternatives(matcher, req.text, _lang(req.lang))


class ReplyRequest(BaseModel):
    result: dict
    alternative: dict | None = None
    lang: str = "ar"


@app.post("/api/reply")
def reply(req: ReplyRequest):
    return extras.reply(req.result, req.alternative, _lang(req.lang))


@app.get("/api/search")
def search(q: str = "", lang: str = "ar", kind: str = "", all: int = 0):
    return extras.search_sources(matcher, q, _lang(lang), kind or None, strong_only=not all)


@app.get("/api/daily")
def daily(lang: str = "ar"):
    return extras.daily(matcher, _lang(lang))


@app.get("/api/dorar")
def dorar_rulings(q: str = ""):
    return dorar.lookup(q)


# Serve the built web app from the same server (one link for the live demo).
dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="web")
