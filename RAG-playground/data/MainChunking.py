"""
Requirements:
    pip install --upgrade requests faiss-cpu sentence-transformers pydantic tiktoken

Environment:
    export GROQ_API_KEY="gsk_..."   # your Groq key

Files:
    - mainData.json  (your integrated professional profile JSON)

Run:
    python rag_integrated_profile.py

What it does:
    1) Build FAISS vector store from mainData.json using LLM-based chunking (Groq)
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
load_dotenv()  # This loads the .env file into os.environ

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE = os.getenv("GROQ_BASE")

# Groq chat models: higher quality for answering
GROQ_ANSWER_MODEL = os.getenv("GROQ_ANSWER_MODEL")

# Local sentence-transformers model for embeddings
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME")

GROQ_CHUNK_MODEL = os.getenv("GROQ_CHUNK_MODEL")

TARGET_TOKENS = 300
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
# Flatten your integrated profile JSON
# -----------------------------
def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def flatten_integrated_profile(doc: Dict[str, Any]) -> List[TextUnit]:
    """Flatten the integrated professional profile JSON into text units for RAG"""
    units: List[TextUnit] = []

    def add_unit(uid: str, text: Optional[str], tags: List[str], src: str):
        if text and str(text).strip():
            units.append(TextUnit(uid, str(text).strip(), tags or [], src))

    # Basic Information
    basic_info = doc.get("basic_info", {})
    if basic_info:
        add_unit(
            "basic_info", 
            f"Name: {basic_info.get('name', '')}\n"
            f"Current Position: {basic_info.get('current_position', '')}\n"
            f"Location: {basic_info.get('location', '')}\n"
            f"Education Status: {basic_info.get('education_status', '')}\n"
            f"Contact: {json.dumps(basic_info.get('contact', {}), indent=2)}\n"
            f"Availability: {json.dumps(basic_info.get('availability', {}), indent=2)}",
            ["basic", "contact", "personal"], 
            "basic_info"
        )

    # Professional Summary
    prof_summary = doc.get("professional_summary", {})
    if prof_summary:
        # Overview
        add_unit("prof_overview", prof_summary.get("overview", ""), ["summary", "overview"], "professional_summary.overview")
        
        # Unique Value Proposition
        uvp_text = "\n".join(prof_summary.get("unique_value_proposition", []))
        if uvp_text:
            add_unit("unique_value_prop", uvp_text, ["uvp", "strengths"], "professional_summary.unique_value_proposition")
        
        # Career Focus
        add_unit("career_focus", prof_summary.get("career_focus", ""), ["career", "focus"], "professional_summary.career_focus")

    # Work Experience
    work_exp = doc.get("work_experience", {})
    if work_exp:
        # Overall experience summary
        add_unit(
            "work_exp_summary",
            f"Total Experience: {work_exp.get('total_experience', '')}\n"
            f"Career Progression: {work_exp.get('career_progression', '')}",
            ["experience", "summary"], 
            "work_experience.summary"
        )
        
        # Individual positions
        for i, pos in enumerate(work_exp.get("positions", [])):
            pos_id = pos.get("id", f"pos_{i}")
            
            # Main position info
            pos_text = (
                f"Company: {pos.get('company', '')}\n"
                f"Position: {pos.get('position', '')} ({pos.get('level', '')})\n"
                f"Duration: {pos.get('duration', '')} ({pos.get('duration_months', '')} months)\n"
                f"Location: {pos.get('location', '')}\n"
                f"Status: {pos.get('status', '')}\n\n"
                f"Key Responsibilities:\n" + "\n".join(f"• {resp}" for resp in pos.get("key_responsibilities", []))
            )
            add_unit(pos_id, pos_text, ["work", "experience", pos.get("level", "").lower()], f"work_experience.positions[{i}]")
            
            # Major projects
            for j, proj in enumerate(pos.get("major_projects", [])):
                proj_id = f"{pos_id}_proj_{j}"
                proj_text = (
                    f"Project: {proj.get('name', '')}\n"
                    f"Description: {proj.get('description', '')}\n"
                    f"Impact: {proj.get('impact', '')}\n"
                    f"Deployment: {proj.get('deployment', '') or ', '.join(proj.get('deployments', []))}"
                )
                add_unit(proj_id, proj_text, ["project", "work", "professional"], f"work_experience.positions[{i}].major_projects[{j}]")

    # Education
    education = doc.get("education", {})
    if education:
        # Formal education
        for i, edu in enumerate(education.get("formal_education", [])):
            edu_id = edu.get("id", f"edu_{i}")
            edu_text = (
                f"Degree: {edu.get('degree', '')}\n"
                f"Field: {edu.get('field', '')}\n"
                f"Institution: {edu.get('institution', '')}\n"
                f"Duration: {edu.get('duration', '')}\n"
                f"Status: {edu.get('status', '')}\n"
                f"Focus Areas: {', '.join(edu.get('focus_areas', []) or edu.get('foundation_areas', []))}"
            )
            add_unit(edu_id, edu_text, ["education", "formal", edu.get("status", "")], f"education.formal_education[{i}]")
        
        # Certifications
        for i, cert in enumerate(education.get("certifications", [])):
            cert_id = f"cert_{i}"
            cert_text = (
                f"Certification: {cert.get('name', '')}\n"
                f"Organization: {cert.get('issuing_organization', '')}\n"
                f"Date: {cert.get('issue_date', '')}\n"
                f"Skills: {', '.join(cert.get('skills_validated', []))}"
            )
            add_unit(cert_id, cert_text, ["certification", "learning"], f"education.certifications[{i}]")

    # Technical Skills
    tech_skills = doc.get("technical_skills", {})
    if tech_skills:
        # Programming Languages
        for i, lang in enumerate(tech_skills.get("programming_languages", [])):
            lang_id = f"lang_{i}"
            lang_text = (
                f"Language: {lang.get('name', '')}\n"
                f"Level: {lang.get('level', '')} (Score: {lang.get('proficiency_score', '')}/10)\n"
                f"Experience: {lang.get('years_experience', '')} years\n"
                f"Specializations: {', '.join(lang.get('specializations', []))}\n"
                f"Frameworks: {', '.join(lang.get('frameworks', []))}\n"
                f"Libraries: {', '.join(lang.get('libraries', []))}\n"
                f"Recent Projects: {', '.join(lang.get('recent_projects', []))}"
            )
            add_unit(lang_id, lang_text, ["skills", "programming", lang.get("level", "")], f"technical_skills.programming_languages[{i}]")
        
        # Frameworks & Libraries
        for i, fw in enumerate(tech_skills.get("frameworks_libraries", [])):
            fw_id = f"framework_{i}"
            fw_text = (
                f"Framework: {fw.get('name', '')}\n"
                f"Category: {fw.get('category', '')}\n"
                f"Level: {fw.get('level', '')} (Score: {fw.get('proficiency_score', '')}/10)\n"
                f"Experience: {fw.get('years_experience', '')} years\n"
                f"Expertise Areas: {', '.join(fw.get('expertise_areas', []))}"
            )
            add_unit(fw_id, fw_text, ["skills", "framework", fw.get("category", "")], f"technical_skills.frameworks_libraries[{i}]")
        
        # Specialized Technologies
        for i, spec in enumerate(tech_skills.get("specialized_technologies", [])):
            spec_id = f"specialized_{i}"
            spec_text = (
                f"Technology: {spec.get('name', '')}\n"
                f"Level: {spec.get('level', '')} (Score: {spec.get('proficiency_score', '')}/10)\n"
                f"Expertise: {', '.join(spec.get('expertise_areas', []))}\n"
                f"Technologies: {', '.join(spec.get('technologies', []))}\n"
                f"Applications: {', '.join(spec.get('applications', []))}"
            )
            add_unit(spec_id, spec_text, ["skills", "specialized", spec.get("name", "").lower().replace(" ", "_")], f"technical_skills.specialized_technologies[{i}]")

    # Projects
    projects = doc.get("projects", {})
    if projects:
        # Featured projects
        for i, proj in enumerate(projects.get("featured_projects", [])):
            proj_id = proj.get("id", f"featured_proj_{i}")
            proj_text = (
                f"Project: {proj.get('name', '')}\n"
                f"Type: {proj.get('type', '')}\n"
                f"Status: {proj.get('status', '')}\n"
                f"Company: {proj.get('company', proj.get('developed at', 'Personal Project'))}\n"
                f"Description: {proj.get('description', '')}\n\n"
                f"Key Features:\n" + "\n".join(f"• {feat}" for feat in proj.get("key_features", [])) + "\n\n"
                f"Technologies: {', '.join(proj.get('technologies', []))}\n"
                f"Impact: {proj.get('impact', '')}"
            )
            add_unit(proj_id, proj_text, ["project", proj.get("category", ""), proj.get("type", "")], f"projects.featured_projects[{i}]")
        
        # Other projects
        for i, proj in enumerate(projects.get("other_projects", [])):
            proj_id = f"other_proj_{i}"
            proj_text = (
                f"Project: {proj.get('name', '')}\n"
                f"Description: {proj.get('description', '')}\n"
                f"Technologies: {', '.join(proj.get('technologies', []))}\n"
                f"Category: {proj.get('category', '')}"
            )
            add_unit(proj_id, proj_text, ["project", proj.get("category", "")], f"projects.other_projects[{i}]")

    # Career Goals
    career_goals = doc.get("career_goals", {})
    if career_goals:
        for goal_type in ["short_term", "medium_term", "long_term"]:
            goal_data = career_goals.get(goal_type, {})
            if goal_data:
                goal_text = (
                    f"Timeline: {goal_data.get('timeline', '')}\n"
                    f"Objectives: {'; '.join(goal_data.get('objectives', []))}\n"
                    f"Vision: {goal_data.get('vision', '')}\n"
                    f"Target Roles: {', '.join(goal_data.get('target_roles', []))}\n"
                    f"Focus Industries: {', '.join(goal_data.get('focus_industries', []))}"
                )
                add_unit(f"goals_{goal_type}", goal_text, ["career", "goals", goal_type], f"career_goals.{goal_type}")
        
        # Mission
        if career_goals.get("mission"):
            add_unit("career_mission", career_goals["mission"], ["career", "mission", "vision"], "career_goals.mission")

    # Personal Interests
    personal_interests = doc.get("personal_interests", {})
    if personal_interests:
        for i, interest in enumerate(personal_interests.get("core_interests", [])):
            interest_id = f"interest_{i}"
            interest_text = (
                f"Interest: {interest.get('name', '')}\n"
                f"Level: {interest.get('level', '')}\n"
                f"Description: {interest.get('description', '')}\n"
                f"Skills Gained: {', '.join(interest.get('skills_gained', []))}"
            )
            add_unit(interest_id, interest_text, ["personal", "interests", interest.get("name", "").lower()], f"personal_interests.core_interests[{i}]")
        
        # Inspirations and lifestyle
        if personal_interests.get("inspirations"):
            add_unit("inspirations", f"Inspirations: {', '.join(personal_interests['inspirations'])}", ["personal", "inspiration"], "personal_interests.inspirations")
        
        if personal_interests.get("lifestyle"):
            add_unit("lifestyle", personal_interests["lifestyle"], ["personal", "lifestyle"], "personal_interests.lifestyle")

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
            return rule_based_split(text)
        arr = json.loads(m.group(0))
        chunks = [c.strip() for c in arr if isinstance(c, str) and c.strip()]
        
        # guardrail long chunks
        trimmed = []
        for c in chunks:
            if len(c) > MAX_CHUNK_CHARS:
                trimmed.extend(rule_based_split(c, MAX_CHUNK_CHARS))
            else:
                trimmed.append(c)
        return trimmed or rule_based_split(text)
    except Exception as e:
        print(f"Groq chunking error: {e}")
        return rule_based_split(text)

def chunk_text_units(units: List[TextUnit]) -> List[Chunk]:
    chunks: List[Chunk] = []
    for u in units:
        pieces = groq_semantic_split(u.text)
        for i, piece in enumerate(pieces, 1):
            chunks.append(Chunk(
                id=f"{u.id}__chunk_{i:02d}",
                text=piece,
                parent_id=u.id,
                tags=u.tags,
                source_path=u.source_path
            ))
        print('goin in')
        time.sleep(2)
    return chunks

# -----------------------------
# Embeddings (local) + FAISS
# -----------------------------
from sentence_transformers import SentenceTransformer

def build_encoder(name: str = EMBED_MODEL_NAME) -> SentenceTransformer:
    return SentenceTransformer(name)

def embed_texts(encoder: SentenceTransformer, texts: List[str]) -> np.ndarray:
    # unnormalized; we'll normalize before indexing
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

    def search(self, query_vec: np.ndarray, k: int = 30) -> List[Dict[str, Any]]:
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

    # system = (
    #     "You are a helpful assistant answering questions about Priyansh Raj's professional profile. "
    #     "Use ONLY the provided context to answer. Be comprehensive: list all relevant items explicitly. "
    #     "Aggregate information from multiple chunks. Structure answers clearly with bullets or numbers. "
    #     "If the answer is not in the context, say you don't know."
    # )    

    # system = (
    #     "You are an intelligent assistant, like Jarvis, answering questions about Priyansh Raj's professional profile. "
    #     "Use ONLY the provided context as your factual base, but respond with clarity, confidence, and structure — like a well-informed AI assistant. "
    #     "Be comprehensive: list all relevant skills, tools, or experiences explicitly. "
    #     "Aggregate and combine information from multiple context chunks if needed. "
    #     "Structure responses using bullet points, numbered lists, or sections for readability. "
    #     "If information is missing from the context, state clearly: 'I don’t have that information.'"
    # )

    system = (
    "You are an intelligent and witty assistant — like Jarvis from Iron Man — answering questions about Priyansh Raj's professional profile. "
    "Use ONLY the provided context as your factual base. Aggregate and connect information across multiple context chunks when needed. "
    "Respond with clarity, confidence, and structure. Be comprehensive: list all relevant skills, tools, or experiences explicitly. "
    "Use bullet points, numbered lists, or clear sections to improve readability. "
    "Inject subtle wit or clever remarks *only* when appropriate — never at the cost of clarity or professionalism. "
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
# Build pipeline
# -----------------------------
def build_store_from_profile(
    json_path: str = "mainData.json",
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

    print("[i] Loading integrated profile JSON…")
    data = load_json(json_path)

    print("[i] Flattening into text units…")
    units = flatten_integrated_profile(data)
    print(f"[i] {len(units)} text units extracted")

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
def retrieve(store: FaissStore, encoder: SentenceTransformer, query: str, k: int = 30) -> List[Dict[str, Any]]:
    q_vec = embed_texts(encoder, [query])
    hits = store.search(q_vec, k=k)
    RELEVANCE_THRESHOLD = 0.60  # Lowered slightly
    hits = [h for h in hits if h["_score"] >= RELEVANCE_THRESHOLD]
    return hits

# -----------------------------
# Main demo
# -----------------------------


if __name__ == "__main__":
    # 1) Build store (or load cache)
    store, encoder = build_store_from_profile(
        json_path="mainData.json", 
        out_dir="vector_store", 
        use_cache=False
    )

    # 2) Try a few queries
    queries = [
        "Projects Priyansh worked on at payguru?",
    ]
    
    for q in queries:
        print("\n" + "="*80)
        print("Q:", q)
        hits = retrieve(store, encoder, q, k=50)
        RELEVANCE_THRESHOLD = 0.5
        hits = [h for h in hits if h["_score"] >= RELEVANCE_THRESHOLD]

        print("\nRetrieved chunks:")
        for i, h in enumerate(hits):
            preview = h["text"].replace("\n", " ")[:160]
            print(f"  {i+1}. {h['_id']} | score={h['_score']:.3f} | tags={h.get('tags', [])} | {preview}…")

        # 3) RAG answer with Groq
        context = "\n\n".join(f"[{i+1}] {h['text']}" for i, h in enumerate(hits))
        answer = groq_answer(q, context)
        print("\nAnswer:")
        print(answer)
        print("\n" + "-"*40)

    