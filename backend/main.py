import os
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path

from rag_engine import answer, ingest_folder, DATA_DIR

app = FastAPI(title="RAG Backend (Gemini + Chroma)")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

class ChatRequest(BaseModel):
    query: str
    k: int = 4

@app.get("/health")
def health():
    return {"ok": True}

# Chat endpoints (both to preserve existing UI shape)
@app.post("/chat")
@app.post("/api/chat")
def chat(req: ChatRequest):
    return answer(req.query, k=req.k)

# Optional: upload & ingest via UI
@app.post("/api/upload")
async def upload(files: List[UploadFile] = File(...)):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    saved = 0
    for f in files:
        dest = DATA_DIR / f.filename
        with dest.open("wb") as out:
            out.write(await f.read())
        saved += 1
    stats = ingest_folder(DATA_DIR)
    return {"saved": saved, **stats}

# CLI trigger to (re)ingest whole folder without upload:
@app.post("/api/ingest")
def api_ingest():
    stats = ingest_folder(DATA_DIR)
    return stats
