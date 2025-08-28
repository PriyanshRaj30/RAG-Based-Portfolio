from __future__ import annotations
import os
import json
import numpy as np
import faiss
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import requests
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from datetime import datetime

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
# Conversation Management
# -----------------------------

@dataclass
class ConversationTurn:
    """Represents a single turn in the conversation"""
    user_message: str
    bot_response: str
    timestamp: str
    retrieved_context: List[Dict[str, Any]]
    
class ConversationManager:
    """Manages conversation history and context"""
    
    def __init__(self, max_turns: int = 10, max_context_length: int = 4000):
        self.conversations: Dict[str, List[ConversationTurn]] = {}
        self.max_turns = max_turns
        self.max_context_length = max_context_length
    
    def add_turn(self, session_id: str, user_message: str, bot_response: str, 
                 retrieved_context: List[Dict[str, Any]]):
        """Add a conversation turn"""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        
        turn = ConversationTurn(
            user_message=user_message,
            bot_response=bot_response,
            timestamp=datetime.now().isoformat(),
            retrieved_context=retrieved_context
        )
        
        self.conversations[session_id].append(turn)
        
        # Keep only the last max_turns
        if len(self.conversations[session_id]) > self.max_turns:
            self.conversations[session_id] = self.conversations[session_id][-self.max_turns:]
    
    def get_conversation_context(self, session_id: str) -> str:
        """Get formatted conversation history for context"""
        if session_id not in self.conversations or not self.conversations[session_id]:
            return ""
        
        context_parts = []
        total_length = 0
        
        # Go through conversation in reverse order (most recent first)
        for turn in reversed(self.conversations[session_id]):
            turn_text = f"User: {turn.user_message}\nAssistant: {turn.bot_response}\n\n"
            
            if total_length + len(turn_text) > self.max_context_length:
                break
            
            context_parts.insert(0, turn_text)
            total_length += len(turn_text)
        
        if context_parts:
            return "Previous conversation:\n" + "".join(context_parts) + "---\n\n"
        return ""
    
    def get_recent_topics(self, session_id: str, num_turns: int = 3) -> List[str]:
        """Extract recent topics/entities mentioned in conversation"""
        if session_id not in self.conversations:
            return []
        
        recent_turns = self.conversations[session_id][-num_turns:]
        topics = []
        
        for turn in recent_turns:
            # Simple topic extraction - you could enhance this with NLP
            words = turn.user_message.lower().split()
            # Look for potential topics (nouns, entities)
            potential_topics = [w for w in words if len(w) > 3 and w.isalpha()]
            topics.extend(potential_topics)
        
        return list(set(topics))  # Remove duplicates

# -----------------------------
# Enhanced Query Processing
# -----------------------------

def enhance_query_with_context(query: str, conversation_context: str, recent_topics: List[str]) -> str:
    """Enhance the query with conversation context for better retrieval"""
    enhanced_query = query
    
    # Add recent topics to improve retrieval
    if recent_topics:
        topic_context = " ".join(recent_topics[:5])  # Use top 5 recent topics
        enhanced_query = f"{query} {topic_context}"
    
    return enhanced_query

def determine_query_intent(query: str, conversation_context: str) -> Dict[str, Any]:
    """Analyze query intent to improve response generation"""
    query_lower = query.lower()
    
    intent_info = {
        "is_followup": bool(conversation_context and any(word in query_lower for word in ["that", "this", "it", "what about", "tell me more", "elaborate"])),
        "is_greeting": any(word in query_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon"]),
        "is_personal": any(word in query_lower for word in ["you", "your", "yourself", "about you"]),
        "is_clarification": any(word in query_lower for word in ["what do you mean", "clarify", "explain", "can you elaborate"]),
        "needs_context": bool(conversation_context and len(query.split()) < 5)
    }
    
    return intent_info

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
# Enhanced retriever
# -----------------------------
def retrieve(store: FaissStore, encoder: SentenceTransformer, query: str, 
             enhanced_query: str, k: int = 60) -> List[Dict[str, Any]]:
    """Retrieve documents using both original and enhanced queries"""
    
    # Get embeddings for both queries
    original_vec = embed_texts(encoder, [query])
    enhanced_vec = embed_texts(encoder, [enhanced_query])
    
    # Search with both queries
    original_hits = store.search(original_vec, k=k//2)
    enhanced_hits = store.search(enhanced_vec, k=k//2)
    
    # Combine and deduplicate results
    seen_ids = set()
    combined_hits = []
    
    for hits in [original_hits, enhanced_hits]:
        for hit in hits:
            if hit["_id"] not in seen_ids:
                seen_ids.add(hit["_id"])
                combined_hits.append(hit)
    
    # Sort by score and apply threshold
    RELEVANCE_THRESHOLD = 0.50
    combined_hits.sort(key=lambda x: x["_score"], reverse=True)
    filtered_hits = [h for h in combined_hits if h["_score"] >= RELEVANCE_THRESHOLD]
    
    return filtered_hits[:k]  # Return top k results

# -----------------------------
# Enhanced Groq answer with conversation context
# -----------------------------
def groq_answer(prompt: str, context: str, conversation_context: str, intent_info: Dict[str, Any]) -> str:
    if not GROQ_API_KEY:
        return "(No GROQ_API_KEY found. Cannot generate answer.)"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }

    # Adapt system prompt based on intent
    base_system = (
        "You are an intelligent assistant answering questions about Priyansh Raj's professional profile. "
        "You have access to conversation history and should provide contextually relevant responses. "
    )
    
    if intent_info.get("is_followup"):
        system_addon = (
            "This appears to be a follow-up question. Reference the previous conversation when relevant. "
            "Use phrases like 'As I mentioned earlier' or 'Building on what we discussed' when appropriate. "
        )
    elif intent_info.get("is_greeting"):
        system_addon = (
            "This is a greeting. Respond warmly and offer to help with questions about Priyansh's profile. "
            "Keep it concise but friendly. "
        )
    elif intent_info.get("is_clarification"):
        system_addon = (
            "The user is asking for clarification. Provide more detailed explanation based on the context. "
            "Break down complex information into clear, understandable parts. "
        )
    else:
        system_addon = (
            "CRITICAL: Answer ONLY what is specifically asked. Do not volunteer additional information unless directly requested. "
            "Use ONLY the provided context as your factual base. "
        )

    system = base_system + system_addon + (
        "Be concise and precise. Use bullet points or clear formatting when listing multiple items. "
        "Add subtle professional wit when appropriate, but prioritize brevity and relevance. "
        "Use emojis sparingly and only when they enhance the response. "
        "If a question cannot be answered using the context, say: 'I don't have that information.' "
        "Remember: Less is more. Answer the question, nothing extra."
    )

    # Construct user prompt with conversation context
    user_prompt_parts = []
    
    if conversation_context:
        user_prompt_parts.append(f"Conversation History:\n{conversation_context}")
    
    user_prompt_parts.extend([
        f"Current Question:\n{prompt}",
        f"Relevant Context:\n{context}",
        "Answer using the context and conversation history when relevant."
    ])
    
    user = "\n\n".join(user_prompt_parts)

    payload = {
        "model": GROQ_ANSWER_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,  # Slightly higher for more natural conversation
        "max_tokens": 500,   # Limit response length
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
# Enhanced Question Answering Function
# -----------------------------
def answer_question(query: str, store: FaissStore, encoder: SentenceTransformer, 
                   conversation_manager: ConversationManager, session_id: str,
                   k: int = 50, relevance_threshold: float = 0.50) -> str:
    """Enhanced question answering with conversation context"""
    
    # Get conversation context
    conversation_context = conversation_manager.get_conversation_context(session_id)
    recent_topics = conversation_manager.get_recent_topics(session_id)
    
    # Analyze query intent
    intent_info = determine_query_intent(query, conversation_context)
    
    # Enhance query for better retrieval
    enhanced_query = enhance_query_with_context(query, conversation_context, recent_topics)
    
    # Retrieve relevant documents
    hits = retrieve(store, encoder, query, enhanced_query, k=k)
    hits = [h for h in hits if h["_score"] >= relevance_threshold]
    
    # Debug information (uncomment if needed)
    # print(f"\nEnhanced query: {enhanced_query}")
    # print(f"Intent: {intent_info}")
    # print(f"Retrieved {len(hits)} chunks")
    
    # Prepare context
    context = "\n\n".join(f"[{i+1}] {h['text']}" for i, h in enumerate(hits))
    
    # Generate answer with conversation context
    answer = groq_answer(query, context, conversation_context, intent_info)
    
    # Store the conversation turn
    conversation_manager.add_turn(session_id, query, answer, hits)
    
    return answer

# -----------------------------
# Enhanced RAG System Class
# -----------------------------
class EnhancedRAGSystem:
    """Main RAG system with conversation management"""
    
    def __init__(self, index_path: str = "vector_store/faiss.index", 
                 meta_path: str = "vector_store/faiss_meta.json"):
        self.store, self.encoder = faiss_loader(index_path, meta_path)
        self.conversation_manager = ConversationManager()
    
    def chat(self, query: str, session_id: str = "default") -> str:
        """Main chat interface"""
        return answer_question(
            query, 
            self.store, 
            self.encoder, 
            self.conversation_manager, 
            session_id
        )
    
    def reset_conversation(self, session_id: str):
        """Reset conversation history for a session"""
        if session_id in self.conversation_manager.conversations:
            del self.conversation_manager.conversations[session_id]
    
    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get conversation summary for analytics"""
        if session_id not in self.conversation_manager.conversations:
            return {"turns": 0, "topics": []}
        
        turns = self.conversation_manager.conversations[session_id]
        return {
            "turns": len(turns),
            "topics": self.conversation_manager.get_recent_topics(session_id, len(turns)),
            "last_interaction": turns[-1].timestamp if turns else None
        }

# -----------------------------
# Main for testing
# -----------------------------
def faiss_loader(index_path="vector_store/faiss.index", meta_path="vector_store/faiss_meta.json"):    
    if not os.path.isfile(index_path) or not os.path.isfile(meta_path):
        print("Error: Vector store not found. Run the build script first with use_cache=False to create it.")
        exit(1)

    print("[i] Loading FAISS store…")
    store = FaissStore.load(index_path, meta_path)
    encoder = build_encoder(EMBED_MODEL_NAME)
    return store, encoder

def retrival_main(question, store, encoder, conversation_manager, session_id="test_session"):    
    print("\n" + "="*80)
    print("Q:", question)
    answer = answer_question(question, store, encoder, conversation_manager, session_id, k=50, relevance_threshold=0.50)
    print("\nAnswer:")
    print(answer)
    print("\n" + "="*80)
    return answer

if __name__ == "__main__":
    # Initialize enhanced RAG system
    rag_system = EnhancedRAGSystem()
    
    # Test conversation flow
    test_session = "test_conversation"
    
    # Simulate a conversation
    queries = [
        "tell me about yourself",
    ]
    
    print("Starting conversation test...")
    for query in queries:
        response = rag_system.chat(query, test_session)
        print(f"\nUser: {query}")
        print(f"Bot: {response}")
        print("-" * 40)
    
    # Show conversation summary
    summary = rag_system.get_conversation_summary(test_session)
    print(f"\nConversation Summary: {summary}")
    