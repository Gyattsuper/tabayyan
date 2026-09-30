"""Tabayyan HTTP API.

  POST /api/check   {"text": "...", "lang": "ar" | "en"}  -> verification results
  GET  /api/health

Run locally:  uvicorn api:app --port 8000
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import ai
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


@app.post("/api/check")
def check(req: CheckRequest):
    if not req.text.strip():
        raise HTTPException(400, "empty text")
    return verify(matcher, req.text, "en" if req.lang == "en" else "ar")


# Serve the built web app from the same server (one link for the live demo).
dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="web")
