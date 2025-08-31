# RAG-Based Portfolio Project

An intelligent portfolio website featuring an AI-powered chatbot that can answer questions about Priyansh Raj's professional profile using Retrieval-Augmented Generation (RAG) technology.

## Features

### Core Functionality
- **Interactive AI Chatbot**: Chat interface that provides contextual answers about professional background
- **Conversation Memory**: Maintains conversation history and context across sessions
- **Smart Retrieval**: Enhanced query processing with FAISS vector search
- **Real-time Responses**: Fast, contextually-aware responses using Groq API
- **Session Management**: Multi-user session support with automatic cleanup

### Technical Highlights
- **RAG Architecture**: Combines document retrieval with language model generation
- **Vector Search**: FAISS-powered semantic search for relevant information retrieval
- **Conversation Context**: Tracks topics and maintains conversation flow
- **Intent Analysis**: Determines query intent for better response generation
- **Session Analytics**: Detailed session statistics and conversation summaries

## Tech Stack

### Backend
- **Python 3.8+** - Core programming language
- **Flask** - Web framework and API server
- **FAISS** - Vector similarity search
- **Sentence Transformers** - Text embedding generation
- **Groq API** - Language model integration
- **NumPy** - Numerical computations

### Frontend
- **HTML5/CSS3** - Structure and styling
- **JavaScript** - Interactive chat interface
- **Font Awesome** - Icons and visual elements

### Dependencies
- `faiss-cpu` - Vector similarity search
- `sentence-transformers` - Text embeddings
- `flask` - Web framework
- `flask-cors` - Cross-origin requests
- `requests` - HTTP client
- `python-dotenv` - Environment configuration
- `numpy` - Numerical operations

## Project Structure

```
portfolio-chatbot/
├── Retrival.py              # Enhanced RAG system implementation
├── app.py                   # Flask backend server
├── templates/
│   └── index.html          # Portfolio HTML template
├── static/
│   ├── styles.css          # Styling (not included)
│   └── script.js           # Frontend JavaScript (not included)
├── vector_store/
│   ├── faiss.index         # FAISS vector index
│   └── faiss_meta.json     # Document metadata
├── .env                    # Environment variables
└── requirements.txt        # Python dependencies
```

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Groq API key

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd portfolio-chatbot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the project root:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_BASE=https://api.groq.com/openai/v1
   GROQ_ANSWER_MODEL=mixtral-8x7b-32768
   EMBED_MODEL_NAME=all-MiniLM-L6-v2
   EMAIL_FROM=your_email@gmail.com
   EMAIL_PASS=your_app_password
   EMAIL_TO=recipient@gmail.com
   FLASK_DEBUG=False
   FLASK_HOST=0.0.0.0
   FLASK_PORT=8000
   SESSION_TIMEOUT_HOURS=24
   MAX_CONCURRENT_SESSIONS=1000
   ```

5. **Prepare vector store**
   Ensure you have the vector store files:
   - `vector_store/faiss.index`
   - `vector_store/faiss_meta.json`
   
   (These should be generated from your document corpus using the RAG build process)

6. **Run the application**
   ```bash
   python app.py
   ```

The application will be available at `http://localhost:8000`

## API Endpoints

### Chat Interface
- **POST** `/api/chat` - Send message to chatbot
  ```json
  {
    "message": "Tell me about your projects",
    "session_id": "optional-session-id",
    "reset_conversation": false
  }
  ```

### Session Management
- **POST** `/api/chat/reset` - Reset conversation history
- **GET** `/api/chat/stats/<session_id>` - Get session statistics
- **GET** `/api/chat/sessions` - List active sessions
- **GET** `/api/chat/history` - Get conversation history

### System Monitoring
- **GET** `/api/health` - Health check endpoint
- **GET** `/api/system/metrics` - System performance metrics

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API key for language model | Required |
| `GROQ_BASE` | Groq API base URL | `https://api.groq.com/openai/v1` |
| `GROQ_ANSWER_MODEL` | Model for generating responses | `mixtral-8x7b-32768` |
| `EMBED_MODEL_NAME` | Sentence transformer model | `all-MiniLM-L6-v2` |
| `FLASK_PORT` | Server port | `8000` |
| `SESSION_TIMEOUT_HOURS` | Session expiry time | `24` |
| `MAX_CONCURRENT_SESSIONS` | Maximum active sessions | `1000` |

### Customization

The chatbot personality can be modified in the `groq_answer` function system prompt. Currently configured with a "Harvey Specter" inspired professional persona.

## Architecture

### RAG Pipeline
1. **Query Enhancement** - Adds conversation context and recent topics
2. **Vector Retrieval** - FAISS search for relevant documents
3. **Context Assembly** - Combines retrieved documents with conversation history
4. **Response Generation** - Groq API generates contextual response
5. **Session Storage** - Saves conversation turn for future context

### Conversation Management
- **Session Tracking** - Each user gets a unique session ID
- **History Retention** - Maintains last 10 conversation turns
- **Topic Extraction** - Identifies and tracks discussed topics
- **Intent Analysis** - Determines query type for better responses

## Usage Examples

### Basic Chat
```javascript
fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: "What programming languages do you know?",
    session_id: "user123"
  })
})
```

### Session Management
```javascript
// Reset conversation
fetch('/api/chat/reset', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ session_id: "user123" })
})

// Get session stats
fetch('/api/chat/stats/user123')
```

## Performance Considerations

- **Vector Search**: FAISS provides sub-millisecond similarity search
- **Session Cleanup**: Automatic cleanup of expired sessions every hour
- **Memory Management**: Limited conversation history to prevent memory bloat
- **Concurrent Handling**: Multi-threaded Flask server for concurrent requests

## Security Features

- **CORS Configuration** - Properly configured cross-origin requests
- **Input Validation** - Validates all incoming requests
- **Session Isolation** - Each session maintains separate conversation context
- **Rate Limiting** - Built-in session limits and timeouts

## Deployment

### Local Development
```bash
python app.py
```

### Production Deployment
Consider using:
- **Gunicorn** for WSGI server
- **Nginx** for reverse proxy
- **Docker** for containerization
- **Environment-specific** configuration files

### Docker Example
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "app.py"]
```

## Monitoring

The application provides several monitoring endpoints:

- **Health Check**: `/api/health` - System status
- **Metrics**: `/api/system/metrics` - Performance statistics
- **Session Info**: Session-level analytics and conversation summaries

## Troubleshooting

### Common Issues

1. **Vector Store Not Found**
   - Ensure `vector_store/faiss.index` and `vector_store/faiss_meta.json` exist
   - Run the document indexing process first

2. **Groq API Errors**
   - Verify `GROQ_API_KEY` is valid
   - Check API quota and rate limits

3. **Memory Issues**
   - Adjust `MAX_CONCURRENT_SESSIONS` based on available memory
   - Monitor session cleanup logs

### Debug Mode
Enable debug mode by setting:
```env
FLASK_DEBUG=True
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is intended for educational and portfolio purposes.

## Contact

For questions or collaboration opportunities:
- **Email**: priyanshraj.dev@gmail.com
- **LinkedIn**: https://www.linkedin.com/in/priyansh-raj/
- **GitHub**: https://github.com/PriyanshRaj30

---

*Built with passion for AI and clean code architecture*