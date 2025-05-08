from flask import Flask, request, jsonify, session
from flask_cors import CORS
import google.generativeai as genai
import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))  # For session management
CORS(app, supports_credentials=True)  # Enable CORS with credentials

# Configure the Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("No GOOGLE_API_KEY found in environment variables")

# Configure the generative AI model
genai.configure(api_key=GOOGLE_API_KEY)

# List of models to try in order of preference
AVAILABLE_MODELS = [
    'gemini-2.0-flash',  # Fastest, good for most use cases
    'gemini-1.5-pro',    # More capable but slower
    'gemini-1.0-pro'     # Fallback option
]

# File to store conversations
CONVERSATIONS_FILE = "conversations.json"

# Initialize conversations storage
def get_conversations():
    if os.path.exists(CONVERSATIONS_FILE):
        try:
            with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_conversations(conversations):
    with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)

# Get available models for debugging
@app.route('/models', methods=['GET'])
def list_models():
    try:
        available_models = genai.list_models()
        model_names = [model.name for model in available_models]
        return jsonify({'available_models': model_names})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_available_model():
    """Try to get an available model that hasn't hit rate limits."""
    for model_name in AVAILABLE_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            # Test the model with a simple prompt
            model.generate_content("test")
            return model
        except Exception as e:
            print(f"Model {model_name} not available: {str(e)}")
            continue
    raise Exception("No available models found. Please try again later.")

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'No message provided'}), 400
        
        user_message = data['message']
        conversation_id = data.get('conversationId')
        
        # Get existing conversations
        conversations = get_conversations()
        
        # Create a new conversation if none exists
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            new_conversation = {
                'id': conversation_id,
                'title': user_message[:30] + '...' if len(user_message) > 30 else user_message,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'messages': []
            }
            conversations.append(new_conversation)
        else:
            # Find existing conversation
            conversation = next((conv for conv in conversations if conv['id'] == conversation_id), None)
            if not conversation:
                return jsonify({'error': 'Conversation not found'}), 404
            conversation['updated_at'] = datetime.now().isoformat()
        
        # Add user message
        current_conversation = next((conv for conv in conversations if conv['id'] == conversation_id), None)
        current_conversation['messages'].append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        try:
            # Try to get an available model
            model = get_available_model()
            response = model.generate_content(user_message)
            response_text = response.text
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            response_text = "I apologize, but I'm currently experiencing high demand. Please try again in a few moments."
        
        # Add AI response
        current_conversation['messages'].append({
            'role': 'assistant',
            'content': response_text,
            'timestamp': datetime.now().isoformat()
        })
        
        # Save updated conversations
        save_conversations(conversations)
        
        return jsonify({
            'response': response_text,
            'conversationId': conversation_id
        })
        
    except Exception as e:
        print(f"General Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200

@app.route('/debug', methods=['GET'])
def debug_info():
    try:
        # Check if API key is set
        api_key_status = "Set" if GOOGLE_API_KEY else "Not set"
        
        # Try to validate API key (this doesn't make an actual model call)
        api_key_valid = "Unknown"
        try:
            # Just check if we can get the models list
            _ = genai.list_models()
            api_key_valid = "Valid"
        except Exception as e:
            api_key_valid = f"Invalid: {str(e)}"
        
        return jsonify({
            'api_key_status': api_key_status,
            'api_key_valid': api_key_valid,
            'google_ai_package_version': genai.__version__
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint to get all conversations
@app.route('/conversations', methods=['GET'])
def get_all_conversations():
    try:
        conversations = get_conversations()
        return jsonify({'conversations': conversations})
    except Exception as e:
        print(f"Error getting conversations: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Endpoint to get a specific conversation
@app.route('/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    try:
        conversations = get_conversations()
        conversation = next((conv for conv in conversations if conv['id'] == conversation_id), None)
        
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        return jsonify(conversation)
    except Exception as e:
        print(f"Error getting conversation: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Endpoint to delete a conversation
@app.route('/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    try:
        conversations = get_conversations()
        conversations = [conv for conv in conversations if conv['id'] != conversation_id]
        save_conversations(conversations)
        return jsonify({'message': 'Conversation deleted successfully'}), 200
    except Exception as e:
        print(f"Error deleting conversation: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Endpoint to delete all conversations
@app.route('/conversations', methods=['DELETE'])
def delete_all_conversations():
    try:
        save_conversations([])
        return jsonify({'message': 'All conversations deleted successfully'}), 200
    except Exception as e:
        print(f"Error deleting all conversations: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Endpoint to update conversation title
@app.route('/conversations/<conversation_id>/title', methods=['PUT'])
def update_conversation_title(conversation_id):
    try:
        data = request.get_json()
        if not data or 'title' not in data:
            return jsonify({'error': 'No title provided'}), 400
        
        conversations = get_conversations()
        conversation = next((conv for conv in conversations if conv['id'] == conversation_id), None)
        
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        conversation['title'] = data['title']
        save_conversations(conversations)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error updating conversation title: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)