import os
from flask import Flask, request, render_template, jsonify, session, send_from_directory, make_response, Response
from werkzeug.utils import secure_filename
import google.generativeai as genai
try:
    import PyPDF2
    from docx import Document
except ImportError:
    print("Warning: PyPDF2 or python-docx not installed. PDF/DOC support will be limited to text files only.")
    # Provide fallback for file reading
    PyPDF2 = None
    Document = None
import re
import requests
from urllib.parse import quote
from dotenv import load_dotenv
from flask_session import Session
from io import BytesIO

# Global storage for uploaded files
UPLOAD_STORAGE = {}

# Set up the Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-dev-secret-key')

# Configure the Gemini API with error handling
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    print(f"Error configuring Gemini API: {str(e)}")

# Enable debug mode
app.debug = True

# Generation config for the model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction="""You are a senior computer science student and a mentor. Format your responses in a clean, readable way:

1. Use clear headings without ## symbols
2. Use bullet points for lists (without showing the - symbol)
3. Emphasize important terms by mentioning them naturally (without ** symbols)
4. Present code examples in code blocks
5. Keep paragraphs short and focused
6. Use natural language for emphasis instead of markdown symbols

At the start of first response, greet the user by name (but only once). Your role is to engage in friendly, curriculum-focused conversations and answer questions in a concise, approachable way. For basic and simple questions, aim to respond with one or two words, but don't be static - add a bit of humor in between the conversation. When explaining concepts, focus only on the essentials, making them easy to understand with relatable analogies and examples."""
)

history = []

if os.getenv('FLASK_ENV') == 'production':
    UPLOAD_FOLDER = None
else:
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SESSION_TYPE'] = 'null'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_file_content(file_data, filename):
    """Read content from different file types stored in memory"""
    file_extension = filename.lower().split('.')[-1]
    
    try:
        if file_extension == 'txt':
            return file_data.decode('utf-8')
                
        elif file_extension == 'pdf':
            if PyPDF2 is None:
                return "PDF support not available. Please install PyPDF2."
            content = []
            pdf_reader = PyPDF2.PdfReader(BytesIO(file_data))
            for page in pdf_reader.pages:
                content.append(page.extract_text())
            return '\n'.join(content)
            
        elif file_extension in ['doc', 'docx']:
            if Document is None:
                return "DOC/DOCX support not available. Please install python-docx."
            doc = Document(BytesIO(file_data))
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            
        else:
            return "Unsupported file format"
            
    except Exception as e:
        print(f"Error reading file {filename}: {str(e)}")
        return f"Error reading file: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/save_user_info', methods=['POST'])
def save_user_info():
    try:
        if request.is_json:
            data = request.get_json()
            name = data.get('name')
            age = data.get('age')
        else:
            name = request.form.get('name')
            age = request.form.get('age')
            
        if not name or not age:
            return jsonify({'status': 'error', 'message': 'Missing name or age'}), 400
            
        # Store in session
        session['user_name'] = name
        session['user_age'] = age
        
        # Clear previous user's history and file content
        global history
        history = []
        if 'uploaded_file' in session:
            # Delete the previous file if it exists
            old_filepath = session['uploaded_file']
            if os.path.exists(old_filepath):
                os.remove(old_filepath)
            session.pop('uploaded_file')
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"Error in save_user_info: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/ask', methods=['POST'])
def ask():
    try:
        user_input = request.form['user_input']
        if not user_input:
            return "Please provide a question", 400

        # Get user info from session
        user_name = session.get('user_name', 'User')
        user_age = session.get('user_age', 'Unknown')
        
        # Get uploaded file content if available
        file_content = ""
        if 'uploaded_file' in session:
            file_key = session['uploaded_file']
            if file_key in UPLOAD_STORAGE:
                file_data = UPLOAD_STORAGE[file_key]
                try:
                    file_content = read_file_content(file_data['data'], file_data['filename'])
                    print(f"File content read successfully: {len(file_content)} characters")
                except Exception as e:
                    print(f"Error reading file content: {str(e)}")
                    file_content = "Error reading file content"

        # Create context-aware message with file content
        context_message = (
            f"Context: You are talking to {user_name}, who is {user_age} years old.\n\n"
            f"File Content: {file_content}\n\n"
            f"User Question: {user_input}\n\n"
            f"Instructions: If the question is about the file content, use the provided file content to answer. "
            f"If the file content is relevant, explicitly reference it in your answer."
        )
        
        # Limit context size if needed
        max_context_length = 30000  # Adjust based on model's limitations
        if len(context_message) > max_context_length:
            context_message = context_message[:max_context_length] + "... (content truncated)"
        
        chat_session = model.start_chat(history=history)
        response = chat_session.send_message(context_message)
        model_response = response.text

        # Store messages in history with context
        history.append({"role": "user", "parts": [user_input]})  # Store only user's question
        history.append({"role": "model", "parts": [model_response]})

        return model_response

    except Exception as e:
        print(f"Error in ask route: {str(e)}")
        return str(e), 500

@app.route('/static/<path:path>')
def send_static(path):
    response = make_response(send_from_directory('static', path))
    # Disable caching for video files
    if path.endswith(('.mp4', '.webm')):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        try:
            # Read file into memory
            file_data = file.read()
            
            # Generate unique key for storage
            file_key = f"{session.get('user_name', 'user')}_{secure_filename(file.filename)}"
            
            # Store in memory
            UPLOAD_STORAGE[file_key] = {
                'data': file_data,
                'filename': file.filename
            }
            
            # Store the key in session
            session['uploaded_file'] = file_key
            
            # Test if we can read the file
            content = read_file_content(file_data, file.filename)
            if content.startswith("Error reading file"):
                raise Exception(content)
            
            return jsonify({
                'status': 'success',
                'message': 'File uploaded and processed successfully'
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error processing file: {str(e)}'
            }), 500
    
    return jsonify({'status': 'error', 'message': 'Invalid file type'}), 400

@app.route('/speak', methods=['POST'])
def speak():
    try:
        text = request.json.get('text')
        if not text:
            return jsonify({'error': 'No text provided'}), 400
            
        # Get user info from session to remove from speech
        user_name = session.get('user_name', 'User')
        
        # Clean the text by removing markdown and special characters
        clean_text = re.sub(r'```[\s\S]*?```', '', text)  # Remove code blocks
        clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_text)  # Remove bold markers
        clean_text = re.sub(r'\*', '', clean_text)  # Remove single asterisks
        clean_text = re.sub(r'^\s*[-•]\s*', '', clean_text, flags=re.MULTILINE)  # Remove bullet points at start of lines
        clean_text = re.sub(r'^\s*\d+\.\s*', '', clean_text, flags=re.MULTILINE)  # Remove numbered list markers
        
        # Handle headers while preserving content
        lines = clean_text.split('\n')
        filtered_lines = []
        for line in lines:
            if not line.strip().startswith('##'):
                # Remove period at end of line only if it's a list item
                if line.strip().startswith('-') or line.strip().startswith('•'):
                    line = re.sub(r'\.$', '', line.strip())
                filtered_lines.append(line)
        clean_text = '\n'.join(filtered_lines)
        
        # Remove remaining markdown elements
        clean_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean_text)  # Remove links but keep text
        clean_text = re.sub(r':[a-zA-Z_]+:', '', clean_text)  # Remove emoji codes
        clean_text = re.sub(r'[\U0001F300-\U0001F9FF]', '', clean_text)  # Remove unicode emojis
        
        # Remove any variations of "Hi {name}" or "Hello {name}" or just the name
        clean_text = re.sub(r'(?i)(hi|hello|hey)\s+' + re.escape(user_name), r'\1', clean_text)
        clean_text = re.sub(re.escape(user_name), '', clean_text)  # Remove remaining instances of the name
        
        # Clean up extra spaces while preserving natural speech pauses
        lines = clean_text.split('\n')
        cleaned_lines = []
        for line in lines:
            if line.strip():
                # Keep periods for actual sentences, remove for list items
                if not (line.strip().startswith('-') or line.strip().startswith('•')):
                    cleaned_lines.append(' '.join(line.split()))
                else:
                    cleaned_lines.append(' '.join(line.split()).rstrip('.'))
        clean_text = ' '.join(cleaned_lines)
        
        return jsonify({'text': clean_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(500)
def handle_500_error(error):
    return jsonify({
        'error': 'Internal Server Error',
        'message': str(error)
    }), 500

@app.errorhandler(Exception)
def handle_exception(error):
    return jsonify({
        'error': 'Unexpected Error',
        'message': str(error)
    }), 500

if __name__ == '__main__':
    is_development = os.getenv('FLASK_ENV') != 'production'
    app.run(debug=is_development)
