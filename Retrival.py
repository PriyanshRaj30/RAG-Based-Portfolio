from __future__ import annotations
import os
import json
import numpy as np
import faiss
from dataclasses import dataclass
from typing import List, Dict, Any
import requests
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# -----------------------------
# Config
# -----------------------------

load_dotenv()  # This loads the .env file into os.environ

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE = os.getenv("GROQ_BASE")

# Groq chat models: higher quality for answering
GROQ_ANSWER_MODEL = os.getenv("GROQ_ANSWER_MODEL")

# Local sentence-transformers model for embeddings
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME")

print(f"GROQ_API_KEY : {GROQ_API_KEY} \n GROQ_BASE: {GROQ_BASE} \n GROQ_ANSWER_MODEL: {GROQ_ANSWER_MODEL} \n EMBED_MODEL_NAME: {EMBED_MODEL_NAME}")
# -----------------------------
# Utilities
# -----------------------------
def http_json_post(url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

# -----------------------------
# Embeddings (local)
# -----------------------------
def build_encoder(name: str = EMBED_MODEL_NAME) -> SentenceTransformer:
    return SentenceTransformer(name)

def embed_texts(encoder: SentenceTransformer, texts: List[str]) -> np.ndarray:
    # unnormalized; we'll normalize before indexing
    vecs = encoder.encode(texts, convert_to_numpy=True, normalize_embeddings=False)
    return np.array(vecs)

# -----------------------------
# FAISS Store
# -----------------------------
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

    def search(self, query_vec: np.ndarray, k: int = 60) -> List[Dict[str, Any]]:
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
# Simple retriever
# -----------------------------
def retrieve(store: FaissStore, encoder: SentenceTransformer, query: str, k: int = 60) -> List[Dict[str, Any]]:
    q_vec = embed_texts(encoder, [query])
    hits = store.search(q_vec, k=k)
    RELEVANCE_THRESHOLD = 0.70  # Lowered slightly
    hits = [h for h in hits if h["_score"] >= RELEVANCE_THRESHOLD]
    return hits

# -----------------------------
# Groq answer
# -----------------------------
def groq_answer(prompt: str, context: str) -> str:
    if not GROQ_API_KEY:
        return "(No GROQ_API_KEY found. Cannot generate answer.)"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }

    system = (
        "You are an intelligent and witty assistant — like Jarvis from Iron Man — answering questions about Priyansh Raj's professional profile. "
        "Use ONLY the provided context as your factual base. Aggregate and connect information across multiple context chunks when needed. "
        "Respond with clarity, confidence, and structure. Be comprehensive: list all relevant skills, tools, or experiences explicitly. "
        "Use bullet points, numbered lists, or clear sections to improve readability. "
        "Inject subtle wit or clever remarks *only* when appropriate — never at the cost of clarity or professionalism. "
        "dont answer in md format, use emojis"
        "If a question cannot be answered using the context, say: 'I don’t have that information.'"
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
        resp = requests.post(
            f"{GROQ_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.HTTPError as e:
        return f"(Groq answer error: {e}, body: {resp.text})"
    except Exception as e:
        return f"(Unexpected Groq error: {e})"

# -----------------------------
# Question Answering Function
# -----------------------------
def answer_question(query: str, store: FaissStore, encoder: SentenceTransformer, k: int = 10, relevance_threshold: float = 0.60) -> str:
    hits = retrieve(store, encoder, query, k=k)
    hits = [h for h in hits if h["_score"] >= relevance_threshold]
    
    # print("\nRetrieved chunks:")
    # for i, h in enumerate(hits):
    #     preview = h["text"].replace("\n", " ")[:160]
        # print(f"  {i+1}. {h['_id']} | score={h['_score']:.3f} | tags={h.get('tags', [])} | {preview}…")

    context = "\n\n".join(f"[{i+1}] {h['text']}" for i, h in enumerate(hits))
    answer = groq_answer(query, context)
    return answer

# -----------------------------
# Main for testing
# -----------------------------
def faiss_loader(index_path ="vector_store/faiss.index",meta_path = "vector_store/faiss_meta.json"):    
    if not os.path.isfile(index_path) or not os.path.isfile(meta_path):
        print("Error: Vector store not found. Run the build script first with use_cache=False to create it.")
        exit(1)

    print("[i] Loading FAISS store…")
    store = FaissStore.load(index_path, meta_path)
    encoder = build_encoder(EMBED_MODEL_NAME)
    return store, encoder

def retrival_main(question, store, encoder):    # Load the pre-built store
    print("\nEnter queries below (empty to quit):")
    q = question
    print("\n" + "="*80)
    print("Q:", q)
    answer = answer_question(q, store, encoder, k=10, relevance_threshold=0.60)
    print("\nAnswer:")
    print(answer)
    print("\n" + "="*80)
    return answer

if __name__ == "__main__":
    index_path = "vector_store/faiss.index"
    meta_path = "vector_store/faiss_meta.json"

    store, encoder = faiss_loader(index_path, meta_path)

    retrival_main("Full name of Priyansh", store, encoder)
    retrival_main("Descrip Priyansh in one word", store, encoder)
