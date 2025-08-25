"""
Requirements:
    pip install --upgrade requests faiss-cpu sentence-transformers pydantic tiktoken

Environment:
    export GROQ_API_KEY="gsk_..."   # your Groq key

Files:
    - personalData.json  (your RAG-optimized JSON from earlier)

Run:
    python rag_groq_faiss.py

What it does:
    1) Build FAISS vector store from personalData.json using LLM-based chunking (Groq)
    2) Run a sample RAG query with Groq chat + retrieved context
"""

from __future__ import annotations
import os, re, json, time
import numpy as np
import faiss
import requests
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

# -----------------------------
# Config
# -----------------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE = os.getenv("GROQ_BASE")

# Groq chat models: higher quality for answering
GROQ_ANSWER_MODEL = os.getenv("GROQ_ANSWER_MODEL")

# Local sentence-transformers model for embeddings
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME")

GROQ_CHUNK_MODEL = "llama-3.1-8b-instant"

# Local sentence-transformers model for embeddings

TARGET_TOKENS = 250
MAX_CHUNK_CHARS = 1600

# -----------------------------
# Data models
# -----------------------------
@dataclass
class TextUnit:
    id: str
    text: str
    tags: List[str]
    source_path: str

@dataclass
class Chunk:
    id: str
    text: str
    parent_id: str
    tags: List[str]
    source_path: str

# -----------------------------
# Utilities
# -----------------------------
def http_json_post(url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

def approx_tokens(s: str) -> int:
    # very rough ~4 chars/token
    return max(1, len(s) // 4)

# -----------------------------
# Flatten your RAG JSON
# -----------------------------
def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def flatten_for_rag(doc: Dict[str, Any]) -> List[TextUnit]:
    units: List[TextUnit] = []

    def add_unit(uid: str, text: Optional[str], tags: List[str], src: str):
        if text and str(text).strip():
            units.append(TextUnit(uid, str(text).strip(), tags or [], src))

    for item in doc.get("basic_info", []):
        uid = item.get("id") or "basic_unk"
        add_unit(uid, item.get("content"), item.get("tags", []), f"basic_info[{uid}].content")

    for item in doc.get("professional_summary", []):
        uid = item.get("id") or "summary_unk"
        add_unit(uid, item.get("content"), item.get("tags", []), f"professional_summary[{uid}]")

    for item in doc.get("unique_value_proposition", []):
        uid = item.get("id") or "uvp_unk"
        add_unit(uid, item.get("content"), item.get("tags", []), f"uvp[{uid}]")

    for item in doc.get("career_goals", []):
        uid = item.get("id") or "goal_unk"
        add_unit(uid, item.get("content"), item.get("tags", []), f"career_goals[{uid}]")

    for item in doc.get("personal_interests", []):
        uid = item.get("id") or "interest_unk"
        text = item.get("description") or item.get("content")
        add_unit(uid, text, item.get("tags", []), f"personal_interests[{uid}]")

    return units

# -----------------------------
# LLM-based semantic chunking (Groq) + fallback
# -----------------------------
def rule_based_split(
    text: str,
    max_chars: int = MAX_CHUNK_CHARS,
    soft_breaks: Tuple[str, ...] = ("\n\n", "\n• ", "\n- ", ". ")
) -> List[str]:
    parts: List[str] = []
    buf = ""
    # split on soft boundaries but pack up to max_chars
    tokens = re.split(r"(\n\n|\n• |\n- |\. )", text)
    print("RULEEEEE BASED FUCKEEEEEEEE")
    for tok in tokens:
        if tok is None:
            continue
        cand = tok if not buf else buf + tok
        if len(cand) <= max_chars:
            buf = cand
        else:
            if buf.strip():
                parts.append(buf.strip())
            buf = tok
    if buf.strip():
        parts.append(buf.strip())

    final = []
    for p in parts:
        if len(p) <= max_chars:
            final.append(p)
        else:
            for i in range(0, len(p), max_chars):
                final.append(p[i:i+max_chars])
    return [c for c in final if c.strip()]

def groq_semantic_split(text: str) -> List[str]:
    if not GROQ_API_KEY:
        # print("NOT API ? WHY FUCKER WHY!?")
        return rule_based_split(text)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }
    system = (
        "You split input text into semantically coherent chunks that preserve meaning. "
        f"Prefer boundaries at topic shifts, bullet lists, or sentence breaks. Aim ~{TARGET_TOKENS} tokens per chunk. "
        "Return ONLY a JSON array of strings, no commentary."
    )
    user = f"Text to split:\n\n{text}\n\nOutput strictly JSON: [\"chunk1\", \"chunk2\", ...]"

    payload = {
        "model": GROQ_CHUNK_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }

    try:
        resp = http_json_post(f"{GROQ_BASE}/chat/completions", headers, payload)
        content = resp["choices"][0]["message"]["content"].strip()
        m = re.search(r"\[.*\]", content, flags=re.S)
        if not m:
            print("HERE1")
            return rule_based_split(text)
        arr = json.loads(m.group(0))
        chunks = [c.strip() for c in arr if isinstance(c, str) and c.strip()]
        print(f"THIS IS THE CHUNKS YOU CHUMPAK! \n\n=====================================\n\n{chunks}")
        # guardrail long chunks
        trimmed = []
        for c in chunks:
            if len(c) > MAX_CHUNK_CHARS:
                trimmed.extend(rule_based_split(c, MAX_CHUNK_CHARS))
            else:
                trimmed.append(c)
        return trimmed or rule_based_split(text)
    except Exception as e:
        print(e)
        print("HERE2")
        return rule_based_split(text)

def chunk_text_units(units: List[TextUnit]) -> List[Chunk]:
    chunks: List[Chunk] = []
    for u in units:
        print(f"\n\n\nUUUUUUUUUu\n {u}")
        pieces = groq_semantic_split(u.text)
        for i, piece in enumerate(pieces, 1):
            chunks.append(Chunk(
                id=f"{u.id}__chunk_{i:02d}",
                text=piece,
                parent_id=u.id,
                tags=u.tags,
                source_path=u.source_path
            ))
    return chunks

# -----------------------------
# Embeddings (local) + FAISS
# -----------------------------
from sentence_transformers import SentenceTransformer

def build_encoder(name: str = EMBED_MODEL_NAME) -> SentenceTransformer:
    return SentenceTransformer(name)

def embed_texts(encoder: SentenceTransformer, texts: List[str]) -> np.ndarray:
    # unnormalized; we’ll normalize before indexing
    vecs = encoder.encode(texts, convert_to_numpy=True, normalize_embeddings=False)
    return np.array(vecs)

class FaissStore:
    def __init__(self, dim: int, index_path: str, meta_path: str):
        self.index = faiss.IndexFlatIP(dim)  # use cosine via normalization
        self.index_path = index_path
        self.meta_path = meta_path
        self.metadatas: List[Dict[str, Any]] = []
        self.ids: List[str] = []

    def add(self, vectors: np.ndarray, metadatas: List[Dict[str, Any]], ids: List[str]):
        assert vectors.shape[0] == len(metadatas) == len(ids)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / np.clip(norms, 1e-12, None)
        self.index.add(vectors.astype("float32"))
        self.metadatas.extend(metadatas)
        self.ids.extend(ids)

    def save(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump({"ids": self.ids, "metadatas": self.metadatas}, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, index_path: str, meta_path: str):
        index = faiss.read_index(index_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        store = cls(index.d, index_path, meta_path)
        store.index = index
        store.ids = meta["ids"]
        store.metadatas = meta["metadatas"]
        return store

    def search(self, query_vec: np.ndarray, k: int = 5) -> List[Dict[str, Any]]:
        q = query_vec / np.clip(np.linalg.norm(query_vec, axis=1, keepdims=True), 1e-12, None)
        D, I = self.index.search(q.astype("float32"), k)
        out = []
        for score, idx in zip(D[0], I[0]):
            if idx == -1:
                continue
            meta = self.metadatas[idx].copy()
            meta["_id"] = self.ids[idx]
            meta["_score"] = float(score)
            out.append(meta)
        return out

# -----------------------------
# RAG: retrieval + Groq answer
# -----------------------------
def groq_answer(prompt: str, context: str) -> str:
    if not GROQ_API_KEY:
        return "(No GROQ_API_KEY found. Cannot generate answer.)"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }

    system = (
        "You are a helpful assistant. Use ONLY the provided context to answer. "
        "If the answer is not in the context, say you don't know."
    )
    user = f"Question:\n{prompt}\n\nContext:\n{context}\n\nAnswer using only the context."

    payload = {
        "model": GROQ_ANSWER_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }

    try:
        print("[DEBUG] Groq chat payload:", json.dumps(payload, indent=2))
        resp = requests.post(
            f"{GROQ_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        print("[DEBUG] Response Status:", resp.status_code)
        print("[DEBUG] Response Body:", resp.text)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.HTTPError as e:
        return f"(Groq answer error: {e}, body: {resp.text})"
    except Exception as e:
        return f"(Unexpected Groq error: {e})"
# -----------------------------
# Build pipeline
# -----------------------------
def build_store_from_profile(
    json_path: str = "personalData.json",
    out_dir: str = "vector_store",
    use_cache: bool = False
) -> Tuple[FaissStore, SentenceTransformer]:
    os.makedirs(out_dir, exist_ok=True)
    index_path = os.path.join(out_dir, "faiss.index")
    meta_path  = os.path.join(out_dir, "faiss_meta.json")

    if use_cache and os.path.isfile(index_path) and os.path.isfile(meta_path):
        print("[i] Loading existing FAISS store…")
        store = FaissStore.load(index_path, meta_path)
        encoder = build_encoder(EMBED_MODEL_NAME)
        return store, encoder

    print("[i] Loading profile JSON…")
    data = load_json(json_path)

    print("[i] Flattening into text units…")
    units = flatten_for_rag(data)
    print(f"[i] {len(units)} text units")

    print("[i] Chunking with Groq (fallback to rule-based if needed)…")
    chunks = chunk_text_units(units)
    print(f"[i] {len(chunks)} chunks produced")

    print("[i] Building embeddings…")
    encoder = build_encoder(EMBED_MODEL_NAME)
    texts = [c.text for c in chunks]
    vecs = embed_texts(encoder, texts)

    print("[i] Creating FAISS store…")
    dim = vecs.shape[1]
    store = FaissStore(dim, index_path, meta_path)

    metadatas = [{
        "chunk_id": c.id,
        "parent_id": c.parent_id,
        "text": c.text,
        "tags": c.tags,
        "source_path": c.source_path
    } for c in chunks]
    ids = [c.id for c in chunks]

    store.add(vecs, metadatas, ids)
    store.save()
    print(f"[✓] Saved index -> {index_path}")
    print(f"[✓] Saved meta  -> {meta_path}")
    return store, encoder

# -----------------------------
# Simple retriever
# -----------------------------
def retrieve(store: FaissStore, encoder: SentenceTransformer, query: str, k: int = 5) -> List[Dict[str, Any]]:
    q_vec = embed_texts(encoder, [query])
    hits = store.search(q_vec, k=k)
    return hits

# -----------------------------
# Main demo
# -----------------------------
if __name__ == "__main__":
    # 1) Build store (or load cache)
    store, encoder = build_store_from_profile(json_path="personalData.json", out_dir="vector_store", use_cache=False)

    # 2) Try a few queries
    queries = [
        "Tell me about Priyansh?"
    ]
    for q in queries:
        print("\n" + "="*80)
        print("Q:", q)
        hits = retrieve(store, encoder, q, k=5)
        for h in hits:
            preview = h["text"].replace("\n", " ")[:160]
            print(f"  - {h['_id']} | score={h['_score']:.3f} | {preview}…")

        # 3) RAG answer with Groq
        context = "\n\n".join(f"[{i+1}] {h['text']}" for i, h in enumerate(hits))
        answer = groq_answer(q, context)
        print("\nAnswer:\n", answer)