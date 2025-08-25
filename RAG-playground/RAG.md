# Personal RAG System: Complete Guide & Walkthrough

## Overview
This guide will walk you through building a Retrieval-Augmented Generation (RAG) system that uses your personal data as a knowledge base. The system will be able to answer questions about you based on the information you provide.

## What is RAG?
RAG combines information retrieval with text generation:
1. **Retrieval**: Search through your personal data to find relevant information
2. **Augmentation**: Add this relevant context to the user's question
3. **Generation**: Use an LLM to generate a response based on the context

## System Architecture
```
User Query → Vector Search → Retrieve Relevant Chunks → LLM + Context → Response
```

## Prerequisites
- Python 3.8+
- Basic understanding of APIs and embeddings
- OpenAI API key (or alternative LLM provider)

## Step 1: Environment Setup

### Install Required Libraries
```bash
pip install openai
pip install chromadb
pip install sentence-transformers
pip install langchain
pip install python-dotenv
pip install streamlit  # for web interface
```

### Project Structure
```
personal_rag/
├── data/
│   ├── personal_info.txt
│   ├── resume.txt
│   └── projects.txt
├── src/
│   ├── __init__.py
│   ├── document_processor.py
│   ├── vector_store.py
│   ├── rag_system.py
│   └── chat_interface.py
├── .env
├── main.py
└── requirements.txt
```

## Step 2: Prepare Your Personal Data

### Create Data Files
Create text files in the `data/` folder with information about yourself:

**personal_info.txt**
```
Name: [Your Name]
Location: [Your City, Country]
Education: [Your degrees and institutions]
Skills: [Programming languages, frameworks, tools]
Interests: [Your hobbies and interests]
Experience: [Brief overview of work experience]
```

**projects.txt**
```
Project 1: [Project Name]
Description: [What the project does]
Technologies: [Languages/frameworks used]
GitHub: [Repository link]

Project 2: [Another project]
...
```

## Step 3: Document Processing

### Create `src/document_processor.py`
```python
import os
from typing import List, Dict
from langchain.text_splitter import RecursiveCharacterTextSplitter

class DocumentProcessor:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def load_documents(self, data_dir: str) -> List[Dict[str, str]]:
        """Load all text files from data directory"""
        documents = []
        
        for filename in os.listdir(data_dir):
            if filename.endswith('.txt'):
                filepath = os.path.join(data_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                    
                documents.append({
                    'content': content,
                    'source': filename,
                    'metadata': {'filename': filename}
                })
        
        return documents
    
    def chunk_documents(self, documents: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Split documents into smaller chunks"""
        chunks = []
        
        for doc in documents:
            text_chunks = self.text_splitter.split_text(doc['content'])
            
            for i, chunk in enumerate(text_chunks):
                chunks.append({
                    'content': chunk,
                    'source': doc['source'],
                    'chunk_id': f"{doc['source']}_{i}",
                    'metadata': doc['metadata']
                })
        
        return chunks
```

## Step 4: Vector Store Setup

### Create `src/vector_store.py`
```python
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import uuid

class VectorStore:
    def __init__(self, collection_name: str = "personal_knowledge"):
        # Initialize ChromaDB
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory="./chroma_db"
        ))
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Personal knowledge base"}
        )
    
    def add_documents(self, chunks: List[Dict[str, str]]):
        """Add document chunks to vector store"""
        texts = [chunk['content'] for chunk in chunks]
        embeddings = self.embedding_model.encode(texts).tolist()
        
        ids = [chunk['chunk_id'] for chunk in chunks]
        metadatas = [chunk['metadata'] for chunk in chunks]
        
        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"Added {len(chunks)} chunks to vector store")
    
    def similarity_search(self, query: str, n_results: int = 3) -> List[Dict]:
        """Search for similar documents"""
        query_embedding = self.embedding_model.encode([query]).tolist()
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['documents'][0])):
            formatted_results.append({
                'content': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if results['distances'] else None
            })
        
        return formatted_results
    
    def persist(self):
        """Persist the database"""
        self.client.persist()
```

## Step 5: RAG System Implementation

### Create `src/rag_system.py`
```python
import openai
from typing import List, Dict
import os
from dotenv import load_dotenv

load_dotenv()

class RAGSystem:
    def __init__(self, vector_store, model_name: str = "gpt-3.5-turbo"):
        self.vector_store = vector_store
        self.model_name = model_name
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        self.system_prompt = """You are a personal assistant that answers questions about the person based on the provided context. 
        Only use information from the context provided. If you cannot find relevant information in the context, 
        say "I don't have that information in my knowledge base."
        
        Be conversational and helpful, and refer to the person in first person when appropriate.
        """
    
    def generate_response(self, query: str, context_docs: List[Dict]) -> str:
        """Generate response using retrieved context"""
        # Combine context documents
        context = "\n\n".join([doc['content'] for doc in context_docs])
        
        # Create the prompt
        prompt = f"""Context information:
{context}

Question: {query}

Please answer the question based on the context information provided above."""

        try:
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def query(self, question: str, n_results: int = 3) -> Dict:
        """Main query method"""
        # Retrieve relevant documents
        relevant_docs = self.vector_store.similarity_search(question, n_results)
        
        # Generate response
        response = self.generate_response(question, relevant_docs)
        
        return {
            'question': question,
            'answer': response,
            'sources': [doc['metadata'] for doc in relevant_docs],
            'context_used': len(relevant_docs)
        }
```

## Step 6: Chat Interface

### Create `src/chat_interface.py`
```python
import streamlit as st
from rag_system import RAGSystem
from vector_store import VectorStore
from document_processor import DocumentProcessor

def initialize_system():
    """Initialize the RAG system"""
    if 'rag_system' not in st.session_state:
        # Initialize components
        processor = DocumentProcessor()
        vector_store = VectorStore()
        
        # Load and process documents
        documents = processor.load_documents('data/')
        chunks = processor.chunk_documents(documents)
        
        # Add to vector store
        vector_store.add_documents(chunks)
        
        # Initialize RAG system
        st.session_state.rag_system = RAGSystem(vector_store)
        st.session_state.messages = []

def main():
    st.title("Personal AI Assistant")
    st.markdown("Ask me anything about myself based on my knowledge base!")
    
    # Initialize system
    initialize_system()
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("What would you like to know?"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = st.session_state.rag_system.query(prompt)
                response = result['answer']
                st.write(response)
                
                # Show sources (optional)
                with st.expander("Sources used"):
                    for source in result['sources']:
                        st.write(f"- {source['filename']}")
        
        # Add assistant response
        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()
```

## Step 7: Main Application

### Create `main.py`
```python
from src.document_processor import DocumentProcessor
from src.vector_store import VectorStore
from src.rag_system import RAGSystem

def setup_knowledge_base():
    """Set up the knowledge base"""
    print("Setting up personal knowledge base...")
    
    # Initialize components
    processor = DocumentProcessor()
    vector_store = VectorStore()
    
    # Load and process documents
    print("Loading documents...")
    documents = processor.load_documents('data/')
    
    print("Chunking documents...")
    chunks = processor.chunk_documents(documents)
    
    print("Adding to vector store...")
    vector_store.add_documents(chunks)
    
    print("Persisting database...")
    vector_store.persist()
    
    return RAGSystem(vector_store)

def interactive_chat(rag_system):
    """Interactive chat loop"""
    print("\nPersonal AI Assistant ready! Type 'quit' to exit.")
    print("Ask me anything about yourself based on your knowledge base.\n")
    
    while True:
        query = input("You: ").strip()
        
        if query.lower() in ['quit', 'exit', 'bye']:
            print("Goodbye!")
            break
        
        if query:
            result = rag_system.query(query)
            print(f"\nAssistant: {result['answer']}\n")

if __name__ == "__main__":
    # Setup
    rag_system = setup_knowledge_base()
    
    # Start interactive chat
    interactive_chat(rag_system)
```

## Step 8: Environment Configuration

### Create `.env` file
```
OPENAI_API_KEY=your_openai_api_key_here
```

### Create `requirements.txt`
```
openai>=1.3.0
chromadb>=0.4.0
sentence-transformers>=2.2.0
langchain>=0.1.0
python-dotenv>=1.0.0
streamlit>=1.28.0
```

## Running the System

### Command Line Interface
```bash
python main.py
```

### Web Interface
```bash
streamlit run src/chat_interface.py
```

## Usage Examples

Once running, you can ask questions like:
- "What programming languages do I know?"
- "Tell me about my projects"
- "What's my educational background?"
- "What are my interests?"

## Customization Options

### 1. Different Embedding Models
```python
# In vector_store.py, replace with:
self.embedding_model = SentenceTransformer('all-mpnet-base-v2')  # Better quality
# or
self.embedding_model = SentenceTransformer('paraphrase-MiniLM-L3-v2')  # Faster
```

### 2. Different LLMs
```python
# Use local models with Ollama
import requests

def query_ollama(prompt):
    response = requests.post('http://localhost:11434/api/generate',
                           json={'model': 'llama2', 'prompt': prompt})
    return response.json()['response']
```

### 3. Advanced Chunking
```python
from langchain.text_splitter import TokenTextSplitter

splitter = TokenTextSplitter(chunk_size=200, chunk_overlap=20)
```

## Portfolio Enhancement Tips

1. **Add evaluation metrics**: Implement relevance scoring for retrieved chunks
2. **Create a dashboard**: Show system statistics and knowledge base contents
3. **Add document upload**: Allow dynamic addition of new information
4. **Implement chat history**: Store and retrieve previous conversations
5. **Add authentication**: Protect your personal information
6. **Deploy online**: Use Streamlit Cloud, Heroku, or similar platforms

## Troubleshooting

### Common Issues
- **API Key errors**: Ensure your OpenAI API key is correct
- **Import errors**: Install all requirements using pip
- **Empty responses**: Check if your data files are properly formatted
- **Slow responses**: Consider using smaller embedding models

### Performance Optimization
- Use batch processing for large document sets
- Implement caching for repeated queries
- Consider using approximate nearest neighbor search for large datasets

## Conclusion

This RAG system creates a personalized AI assistant that knows about you based on your own data. It's an excellent portfolio project that demonstrates:
- Understanding of vector databases and embeddings
- Integration of multiple AI technologies
- System design and architecture skills
- Full-stack development capabilities

The system is extensible and can be enhanced with additional features like web scraping your social media, integration with your calendar, or connection to your GitHub repositories for a more comprehensive personal knowledge base.