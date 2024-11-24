import os
from flask import Flask, request, render_template
import google.generativeai as genai
from flask import session

# Configure the Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Set up the Flask app
app = Flask(__name__)

# Add secret key for session management
app.secret_key = os.getenv("SECRET_KEY", "your-default-secret-key")  # Better to use environment variable

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
    system_instruction="You are a senior computer science student and a mentor. At the start of each conversation, greet the user by name (but only once). Your role is to engage in friendly, curriculum-focused conversations and answer questions in a concise, approachable way.For basic and simple questions, aim to respond with one or two words, unless the user asks for a detailed explanation. Keep your answers brief and straightforward to maintain a natural flow in simpler conversations. When explaining concepts, focus only on the essentials, making them easy to understand with relatable analogies and examples.Use humor to make the conversation both educational and enjoyable.For links, provide only valid, accessible websites when requested, avoiding closed or inaccessible sources. For current events, news, or sports updates, use the Gemini tool to provide accurate, up-to-date information.Relate academic concepts to real-world observations and experiments, suggesting practical ways for users to connect what they learn to their experiences.",)

history = []

@app.route('/')
def index():
    # Clear any existing session data when visiting home page
    session.clear()
    return render_template('index.html')

@app.route('/save_user_info', methods=['POST'])
def save_user_info():
    # Save user info to session
    session['user_name'] = request.form['name']
    session['user_age'] = request.form['age']
    return {'status': 'success'}

@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form['user_input']
    
    # Get user info from session
    user_name = session.get('user_name', 'User')
    user_age = session.get('user_age', 'Unknown')
    
    # Create context-aware message with explicit instruction about name usage
    context_message = (
        f"Remember that you're talking to {user_name}, who is {user_age} years old. "
        f"Always refer to them by their name ({user_name}) when appropriate in your responses. "
        f"User's message: {user_input}"
    )
    
    chat_session = model.start_chat(history=history)
    response = chat_session.send_message(context_message)
    model_response = response.text

    # Store messages in history with context
    history.append({"role": "user", "parts": [context_message]})
    history.append({"role": "model", "parts": [model_response]})

    return model_response

if __name__ == '__main__':
    app.run(debug=True)
