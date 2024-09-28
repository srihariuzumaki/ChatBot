import os
from flask import Flask, request, render_template
import google.generativeai as genai

# Configure the Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Set up the Flask app
app = Flask(__name__)

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
    system_instruction="You are senior of a computer degree student and a mentor. and you have to ask the user name while begining the conversation . and after that you have to address the user by their name ! but dont call thier name  .say it only once at the starting at the chat , Your task is to engage in conversations about the curriculam and answer questions. but dont give long responses for a simple conversarion rather make it friendly way for normal questions . and try to give a one word or two word answers for basic and simple questions like what can you do and other simple questions unless they ask in detail about it, only Explain the necessary  concepts so that they are easily understandable. Use analogies and examples that are relatable. Use humor and make the conversation both educational and interesting.and you must provide the necessary links to the user if they ask for it and only give the links of the websites which are valid and not a closed website . and give any type of the answer to the user without any hesitation like present news and sports related news and give the latest information by using gemini etc,Suggest way that these concepts can be related to the real world with observations and experiments",)

history = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form['user_input']
    
    chat_session = model.start_chat(history=history)
    response = chat_session.send_message(user_input)
    model_response = response.text

    history.append({"role": "user", "parts": [user_input]})
    history.append({"role": "model", "parts": [model_response]})

    return model_response

if __name__ == '__main__':
    app.run(debug=True)
