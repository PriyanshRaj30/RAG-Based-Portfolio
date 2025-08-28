"""
Portfolio Chatbot Backend with Enhanced RAG and Conversation History
A Flask-based API for handling chat interactions in the developer portfolio
"""

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import logging
import os
from typing import Dict, Any, Optional
import threading
from Retrival import EnhancedRAGSystem  # Import the enhanced RAG system

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Enable CORS for frontend-backend communication

# Configuration
class Config:
    """Application configuration"""
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', 8000))
    
    # Session management
    SESSION_TIMEOUT_HOURS = int(os.environ.get('SESSION_TIMEOUT_HOURS', 24))
    MAX_CONCURRENT_SESSIONS = int(os.environ.get('MAX_CONCURRENT_SESSIONS', 1000))
 
app.config.from_object(Config)

# Enhanced chatbot with conversation history
class EnhancedChatbotHandler:
    """
    Enhanced chatbot handler with conversation management
    """
    
    def __init__(self):
        try:
            # Initialize the enhanced RAG system
            index_path = "vector_store/faiss.index"
            meta_path = "vector_store/faiss_meta.json"
            self.rag_system = EnhancedRAGSystem(index_path, meta_path)
            logger.info("Enhanced RAG system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {str(e)}")
            self.rag_system = None
        
        # Session management
        self.session_data = {}  # Store session metadata
        self.session_lock = threading.Lock()
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_expired_sessions, daemon=True)
        self.cleanup_thread.start()
    
    def process_message(self, message: str, session_id: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a message and return enhanced response with metadata"""
        
        if not self.rag_system:
            return {
                'response': "I'm currently unavailable. Please try again later.",
                'error': 'RAG system not initialized',
                'session_info': {}
            }
        
        try:
            # Update session activity
            self._update_session_activity(session_id)
            
            # Get response from RAG system
            response = 'self.rag_system'.chat(message, session_id)
            
            # Get conversation summary for metadata
            conv_summary = self.rag_system.get_conversation_summary(session_id)
            
            # Prepare session info
            session_info = {
                'turn_count': conv_summary.get('turns', 0),
                'topics_discussed': conv_summary.get('topics', [])[:5],  # Top 5 topics
                'last_interaction': conv_summary.get('last_interaction'),
                'session_duration': self._get_session_duration(session_id)
            }
            
            return {
                'response': response,
                'session_info': session_info,
                'success': True
            }
        
        except Exception as e:
            logger.error(f"Error processing message for session {session_id}: {str(e)}")
            return {
                'response': "I encountered an error processing your message. Please try again.",
                'error': str(e),
                'session_info': {},
                'success': False
            }
    
    def reset_conversation(self, session_id: str) -> bool:
        """Reset conversation for a session"""
        try:
            if self.rag_system:
                self.rag_system.reset_conversation(session_id)
            
            with self.session_lock:
                if session_id in self.session_data:
                    # Keep session data but mark as reset
                    self.session_data[session_id]['reset_at'] = datetime.now()
            
            logger.info(f"Reset conversation for session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error resetting conversation for session {session_id}: {str(e)}")
            return False
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get detailed session statistics"""
        try:
            if not self.rag_system:
                return {}
            
            conv_summary = self.rag_system.get_conversation_summary(session_id)
            
            with self.session_lock:
                session_meta = self.session_data.get(session_id, {})
            
            return {
                'session_id': session_id,
                'conversation_turns': conv_summary.get('turns', 0),
                'topics_discussed': conv_summary.get('topics', []),
                'session_started': session_meta.get('created_at'),
                'last_activity': session_meta.get('last_activity'),
                'session_duration_minutes': self._get_session_duration(session_id),
                'total_messages': session_meta.get('message_count', 0)
            }
        except Exception as e:
            logger.error(f"Error getting session stats for {session_id}: {str(e)}")
            return {'error': str(e)}
    
    def _update_session_activity(self, session_id: str):
        """Update session activity timestamp and metadata"""
        with self.session_lock:
            now = datetime.now()
            
            if session_id not in self.session_data:
                self.session_data[session_id] = {
                    'created_at': now,
                    'message_count': 0
                }
            
            self.session_data[session_id].update({
                'last_activity': now,
                'message_count': self.session_data[session_id].get('message_count', 0) + 1
            })
    
    def _get_session_duration(self, session_id: str) -> float:
        """Get session duration in minutes"""
        with self.session_lock:
            session_meta = self.session_data.get(session_id)
            if not session_meta:
                return 0.0
            
            created_at = session_meta.get('created_at')
            last_activity = session_meta.get('last_activity', datetime.now())
            
            if created_at:
                duration = last_activity - created_at
                return round(duration.total_seconds() / 60, 2)
            return 0.0
    
    def _cleanup_expired_sessions(self):
        """Background task to cleanup expired sessions"""
        import time
        
        while True:
            try:
                time.sleep(3600)  # Check every hour
                
                cutoff_time = datetime.now() - timedelta(hours=app.config['SESSION_TIMEOUT_HOURS'])
                expired_sessions = []
                
                with self.session_lock:
                    for session_id, data in self.session_data.items():
                        last_activity = data.get('last_activity', data.get('created_at'))
                        if last_activity and last_activity < cutoff_time:
                            expired_sessions.append(session_id)
                    
                    # Remove expired sessions
                    for session_id in expired_sessions:
                        del self.session_data[session_id]
                        if self.rag_system:
                            self.rag_system.reset_conversation(session_id)
                
                if expired_sessions:
                    logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
            except Exception as e:
                logger.error(f"Error in session cleanup: {str(e)}")

# Initialize enhanced chatbot
chatbot = EnhancedChatbotHandler()

@app.route('/')
def index():
    """Serve the main portfolio page"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handle chat messages with enhanced conversation management
    
    Expected JSON payload:
    {
        "message": "User's message",
        "session_id": "optional-session-id",
        "timestamp": "optional-timestamp",
        "reset_conversation": false  // optional flag to reset
    }
    
    Returns:
    {
        "response": "Bot's response",
        "timestamp": "2024-01-01T12:00:01Z",
        "session_info": {
            "turn_count": 5,
            "topics_discussed": ["skills", "projects"],
            "session_duration": 15.5
        },
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
        
        # Extract session information
        session_id = data.get('session_id', f'session_{datetime.now().timestamp()}')
        user_timestamp = data.get('timestamp')
        reset_conversation = data.get('reset_conversation', False)
        
        # Reset conversation if requested
        if reset_conversation:
            chatbot.reset_conversation(session_id)
        
        # Log the interaction
        logger.info(f"Processing message from session {session_id}: {user_message[:100]}...")
        
        # Prepare user context
        user_context = {
            'session_id': session_id,
            'timestamp': user_timestamp,
            'user_agent': request.headers.get('User-Agent', ''),
            'ip_address': request.remote_addr
        }
        
        # Process message with enhanced chatbot
        result = chatbot.process_message(user_message, session_id, user_context)
        
        # Prepare response
        response_data = {
            'response': result.get('response', 'No response generated'),
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'session_info': result.get('session_info', {}),
            'success': result.get('success', True)
        }
        
        # Add error info if present
        if 'error' in result:
            response_data['error'] = result['error']
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'success': False
        }), 500

@app.route('/api/chat/reset', methods=['POST'])
def reset_conversation():
    """Reset conversation for a session"""
    try:
        data = request.get_json() if request.is_json else {}
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                'error': 'session_id is required',
                'success': False
            }), 400
        
        success = chatbot.reset_conversation(session_id)
        
        return jsonify({
            'message': f'Conversation reset for session {session_id}',
            'success': success
        })
    
    except Exception as e:
        logger.error(f"Error resetting conversation: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'success': False
        }), 500

@app.route('/api/chat/stats/<session_id>', methods=['GET'])
def get_session_stats(session_id: str):
    """Get detailed statistics for a session"""
    try:
        stats = chatbot.get_session_stats(session_id)
        
        return jsonify({
            'stats': stats,
            'success': True
        })
    
    except Exception as e:
        logger.error(f"Error getting session stats: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'success': False
        }), 500

@app.route('/api/chat/sessions', methods=['GET'])
def get_active_sessions():
    """Get list of active sessions (for admin/debugging)"""
    try:
        with chatbot.session_lock:
            active_sessions = []
            
            for session_id, data in chatbot.session_data.items():
                session_info = {
                    'session_id': session_id,
                    'created_at': data.get('created_at').isoformat() if data.get('created_at') else None,
                    'last_activity': data.get('last_activity').isoformat() if data.get('last_activity') else None,
                    'message_count': data.get('message_count', 0),
                    'duration_minutes': chatbot._get_session_duration(session_id)
                }
                active_sessions.append(session_info)
        
        # Sort by last activity (most recent first)
        active_sessions.sort(key=lambda x: x.get('last_activity', ''), reverse=True)
        
        return jsonify({
            'active_sessions': active_sessions,
            'total_count': len(active_sessions),
            'success': True
        })
    
    except Exception as e:
        logger.error(f"Error getting active sessions: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'success': False
        }), 500

@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    """
    Get chat history - now provides session-based information
    Query parameters:
    - session_id: Filter by session (required)
    - format: 'summary' or 'detailed' (default: summary)
    """
    try:
        session_id = request.args.get('session_id')
        format_type = request.args.get('format', 'summary')
        
        if not session_id:
            return jsonify({
                'error': 'session_id parameter is required',
                'success': False
            }), 400
        
        if format_type == 'detailed':
            # Get detailed session stats
            stats = chatbot.get_session_stats(session_id)
            return jsonify({
                'session_stats': stats,
                'success': True
            })
        else:
            # Get summary information
            if not chatbot.rag_system:
                return jsonify({
                    'error': 'RAG system not available',
                    'success': False
                }), 503
            
            conv_summary = chatbot.rag_system.get_conversation_summary(session_id)
            
            with chatbot.session_lock:
                session_meta = chatbot.session_data.get(session_id, {})
            
            summary = {
                'session_id': session_id,
                'turn_count': conv_summary.get('turns', 0),
                'topics': conv_summary.get('topics', [])[:10],  # Top 10 topics
                'last_interaction': conv_summary.get('last_interaction'),
                'session_duration_minutes': chatbot._get_session_duration(session_id),
                'message_count': session_meta.get('message_count', 0)
            }
            
            return jsonify({
                'summary': summary,
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
    """Enhanced health check endpoint"""
    try:
        # Check RAG system status
        rag_status = "healthy" if chatbot.rag_system else "unavailable"
        
        # Get system stats
        with chatbot.session_lock:
            active_session_count = len(chatbot.session_data)
        
        health_info = {
            'status': 'healthy' if rag_status == "healthy" else 'degraded',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0',
            'components': {
                'rag_system': rag_status,
                'session_manager': 'healthy',
                'vector_store': 'healthy' if rag_status == "healthy" else 'unknown'
            },
            'metrics': {
                'active_sessions': active_session_count,
                'max_sessions': app.config['MAX_CONCURRENT_SESSIONS'],
                'session_timeout_hours': app.config['SESSION_TIMEOUT_HOURS']
            }
        }
        
        status_code = 200 if health_info['status'] == 'healthy' else 503
        return jsonify(health_info), status_code
    
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503

@app.route('/api/system/metrics', methods=['GET'])
def system_metrics():
    """Get system performance metrics"""
    try:
        with chatbot.session_lock:
            session_count = len(chatbot.session_data)
            
            # Calculate session statistics
            if chatbot.session_data:
                message_counts = [data.get('message_count', 0) for data in chatbot.session_data.values()]
                avg_messages = sum(message_counts) / len(message_counts)
                total_messages = sum(message_counts)
                
                durations = [chatbot._get_session_duration(sid) for sid in chatbot.session_data.keys()]
                avg_duration = sum(durations) / len(durations) if durations else 0
            else:
                avg_messages = 0
                total_messages = 0
                avg_duration = 0
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'sessions': {
                'active_count': session_count,
                'max_allowed': app.config['MAX_CONCURRENT_SESSIONS'],
                'utilization_percent': round((session_count / app.config['MAX_CONCURRENT_SESSIONS']) * 100, 2)
            },
            'messages': {
                'total_processed': total_messages,
                'average_per_session': round(avg_messages, 2)
            },
            'performance': {
                'average_session_duration_minutes': round(avg_duration, 2),
                'rag_system_status': 'operational' if chatbot.rag_system else 'unavailable'
            }
        }
        
        return jsonify({
            'metrics': metrics,
            'success': True
        })
    
    except Exception as e:
        logger.error(f"Error getting system metrics: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'success': False
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'success': False,
        'available_endpoints': [
            'GET /',
            'POST /api/chat',
            'POST /api/chat/reset',
            'GET /api/chat/stats/<session_id>',
            'GET /api/chat/sessions',
            'GET /api/chat/history',
            'GET /api/health',
            'GET /api/system/metrics'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'error': 'Internal server error',
        'success': False
    }), 500

@app.before_request
def log_request():
    """Log incoming requests for debugging"""
    if request.endpoint and not request.endpoint.startswith('static'):
        logger.info(f"{request.method} {request.path} from {request.remote_addr}")

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('vector_store', exist_ok=True)
    
    logger.info("Starting Enhanced Portfolio Chatbot Server...")
    logger.info(f"Debug mode: {app.config['DEBUG']}")
    logger.info(f"Session timeout: {app.config['SESSION_TIMEOUT_HOURS']} hours")
    logger.info(f"Max concurrent sessions: {app.config['MAX_CONCURRENT_SESSIONS']}")
    
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG'],
        threaded=True  # Enable threading for concurrent requests
    )