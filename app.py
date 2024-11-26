import os
from flask import Flask, request, render_template, jsonify
import google.generativeai as genai
from flask import jsonify
from flask import session

# Configure the Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Set up the Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # replace with a real secret key

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
    system_instruction="You are a senior computer science student and a mentor. At the start of each conversation, greet the user by name (but only once). Your role is to engage in friendly, curriculum-focused conversations and answer questions in a concise, approachable way.For basic and simple questions, aim to respond with one or two words, but dont be static add a bit of a humor in between the conversation  When explaining concepts, focus only on the essentials, making them easy to understand with relatable analogies and examples.Use humor to make the conversation both educational and enjoyable.For links, provide only valid, accessible websites when requested, avoiding closed or inaccessible sources. For current events, news, or sports updates, use the Gemini tool to provide accurate, up-to-date information.Relate academic concepts to real-world observations and experiments, suggesting practical ways for users to connect what they learn to their experiences.",)

history = []

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
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"Error in save_user_info: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form['user_input']
    
    # Get user info from session
    user_name = session.get('user_name', 'User')
    user_age = session.get('user_age', 'Unknown')
    
    # Create context-aware message with explicit instruction about name usage
    context_message = (
        f"Remember that you're talking to {user_name}, who is {user_age} years old. "
        
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
