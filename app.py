"""
Portfolio Chatbot Backend
A Flask-based API for handling chat interactions in the developer portfolio
"""

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from datetime import datetime
import json
import logging
import os
import Retrival

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# static_folder='static' ==> This tells Flask where to find static files, like: -> CSS, JavaScript, Images
# template_folder='templates' ==> This tells Flask where to find HTML template files (like .html files for rendering views).

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Enable CORS for frontend-backend communication

# Configuration
class Config:
    """Application configuration"""
    # SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', 8000))

app.config.from_object(Config)

# In-memory storage for chat history (replace with database in production)
chat_history = []

class ChatbotResponse:
    """
    Placeholder chatbot response handler
    Replace this class with your actual chatbot implementation
    """
    
    def __init__(self):
        self.responses = {}
        index_path = "vector_store/faiss.index"
        meta_path = "vector_store/faiss_meta.json"
        self.store, self.encoder = Retrival.faiss_loader(index_path, meta_path)


    def process_message(self, message, user_context=None):
        return self._generate_placeholder_response(message)
    
    def _generate_placeholder_response(self, question):
        """Generate a placeholder response for development"""
        # return (
        #     f"Thanks for your message: '{message}'. "
        #     "I'm currently being developed and will have intelligent responses soon! "
        #     "The developer is working on implementing advanced NLP capabilities."
        # )

        answer = Retrival.retrival_main(question, self.store, self.encoder)
        return answer
    
# Initialize chatbot
chatbot = ChatbotResponse()

@app.route('/')
def index():
    """Serve the main portfolio page"""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handle chat messages from the frontend
    
    Expected JSON payload:
    {
        "message": "User's message",
        "timestamp": "2024-01-01T12:00:00Z",
        "session_id": "optional-session-id"
    }
    
    Returns:
    {
        "response": "Bot's response",
        "timestamp": "2024-01-01T12:00:01Z",
        "success": true
    }
    """
    try:
        # Validate request
        if not request.is_json:
            return jsonify({
                'error': 'Content-Type must be application/json',
                'success': False
            }), 400
        
        data = request.get_json()
        
        # Validate required fields
        if 'message' not in data:
            return jsonify({
                'error': 'Message field is required',
                'success': False
            }), 400
        
        user_message = data['message'].strip()
        if not user_message:
            return jsonify({
                'error': 'Message cannot be empty',
                'success': False
            }), 400
        
        # Extract optional fields
        user_timestamp = data.get('timestamp')
        session_id = data.get('session_id', 'anonymous')
        
        # Log the interaction
        logger.info(f"Received message from {session_id}: {user_message[:100]}...")
        
        # Store chat history
        chat_entry = {
            'session_id': session_id,
            'user_message': user_message,
            'timestamp': user_timestamp or datetime.now().isoformat(),
            'processed_at': datetime.now().isoformat()
        }
        
        # Process message with chatbot
        user_context = {
            'session_id': session_id,
            'timestamp': user_timestamp,
            'chat_history': [entry for entry in chat_history if entry['session_id'] == session_id]
        }
        
        bot_response = chatbot.process_message(user_message, user_context)
        
        # Add bot response to chat entry
        chat_entry['bot_response'] = bot_response
        chat_history.append(chat_entry)
        
        # Keep only last 1000 chat entries (memory management)
        if len(chat_history) > 1000:
            chat_history[:] = chat_history[-1000:]
        
        # Return response
        return jsonify({
            'response': bot_response,
            'timestamp': datetime.now().isoformat(),
            'success': True
        })
    
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'success': False
        }), 500

@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    """
    Get chat history for debugging/analytics
    Optional query parameters:
    - session_id: Filter by session
    - limit: Limit number of results (default: 50)
    """
    try:
        session_id = request.args.get('session_id')
        limit = min(int(request.args.get('limit', 50)), 1000)  # Max 1000 entries
        
        # Filter and limit results
        filtered_history = chat_history
        if session_id:
            filtered_history = [entry for entry in chat_history if entry['session_id'] == session_id]
        
        # Return most recent entries
        recent_history = filtered_history[-limit:] if filtered_history else []
        
        return jsonify({
            'history': recent_history,
            'total_count': len(filtered_history),
            'success': True
        })
    
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'success': False
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'success': False
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'error': 'Internal server error',
        'success': False
    }), 500

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    logger.info("Starting Portfolio Chatbot Server...")
    logger.info(f"Debug mode: {app.config['DEBUG']}")
    
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )