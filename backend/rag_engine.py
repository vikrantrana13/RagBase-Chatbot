import os, uuid
from pathlib import Path
from typing import List, Tuple, Dict, Any

import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader

from google import genai
from google.genai import types

from dotenv import load_dotenv 

# ---------- Config ----------
load_dotenv()           
CHROMA_DIR = os.getenv("CHROMA_DIR", ".chroma")
GENERATION_MODEL = os.getenv("GENERATION_MODEL", "gemini-2.0-flash-001")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")  # GA model
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))

# Gemini client (reads GOOGLE_API_KEY or Vertex envs)
client = genai.Client(api_key=os.getenv("AIzaSyCSnifbfHBPBk_dFACPcZjvG85nF9xFSFs"))

# Chroma persistent store
chroma = chromadb.PersistentClient(path=CHROMA_DIR)
collection = chroma.get_or_create_collection(
    name="docs",
    metadata={"hnsw:space": "cosine"}
)

# ---------- Embeddings ----------
def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Uses Google GenAI embed_content. Handles single/batch responses.
    """
    resp = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts if len(texts) > 1 else texts[0],
        # You can set output_dimensionality via config if you want smaller vectors:
        # config=types.EmbedContentConfig(output_dimensionality=1024),
    )
    # Response shape is SDK-specific; normalize to a list of vectors:
    if hasattr(resp, "embeddings"):
        embs = []
        for e in (resp.embeddings if isinstance(resp.embeddings, list) else [resp.embeddings]):
            # most SDK builds expose .values as the raw vector
            vals = getattr(e, "values", None)
            if vals is None and isinstance(e, dict):
                vals = e.get("values")
            if vals is None:
                raise RuntimeError("Unexpected embedding response shape.")
            embs.append(list(vals))
        return embs
    raise RuntimeError("No embeddings in response.")

# ---------- Chunking / Loading ----------
def _chunks(text: str, max_words: int = 500):
    words = text.split()
    for i in range(0, len(words), max_words):
        yield " ".join(words[i : i + max_words])

def _load_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    return path.read_text(encoding="utf-8", errors="ignore")

# ---------- Ingest ----------
def ingest_folder(folder: Path = DATA_DIR) -> Dict[str, Any]:
    docs, ids, metas = [], [], []
    files = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in {".pdf", ".txt", ".md"}]
    if not files:
        return {"indexed": 0, "files": 0}

    for f in files:
        raw = _load_text(f)
        for i, chunk in enumerate(_chunks(raw)):
            docs.append(chunk)
            ids.append(str(uuid.uuid4()))
            metas.append({"source": f.name})
    # embed + add
    embs = embed_texts(docs)
    collection.add(documents=docs, embeddings=embs, ids=ids, metadatas=metas)
    return {"indexed": len(docs), "files": len(files)}

# ---------- Retrieve + Generate ----------
def _retrieve(query: str, k: int = 4) -> List[Tuple[str, str]]:
    q_emb = embed_texts([query])[0]
    res = collection.query(
        query_embeddings=[q_emb],
        n_results=k,
        include=["documents", "metadatas"]
    )
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    return [(doc, (meta or {}).get("source", "unknown")) for doc, meta in zip(docs, metas)]

def _build_prompt(query: str, contexts: List[str]) -> str:
    return (
        "You are a helpful RAG assistant. Use ONLY the provided context.\n"
        "If the answer isn't present, say you don't know.\n\n"
        f"Question: {query}\n\nContext:\n" + "\n---\n".join(contexts) + "\n\nAnswer with brief citations like [source]."
    )

def answer(query: str, k: int = 4) -> Dict[str, Any]:
    hits = _retrieve(query, k=k)
    ctx = [d for d, _ in hits] or ["(no relevant context)"]
    prompt = _build_prompt(query, ctx)

    resp = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2),
    )
    text = getattr(resp, "text", None) or str(resp)
    return {"answer": text, "sources": [s for _, s in hits]}
