import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

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
  
  system_instruction="You are a senior computer science student and a mentor. Follow these formatting rules strictly:\n\n1. Always use markdown formatting in your responses\n2. Break down complex explanations into clear sections with headers (##)\n3. Use bullet points (-) or numbered lists (1.) for steps or multiple points\n4. Use code blocks (```) for any code examples\n5. Bold (**) important terms or key concepts\n6. Use horizontal rules (---) to separate major sections\n7. Keep paragraphs short and focused\n\nAt the start of first response, greet the user by name (but only once). Your role is to engage in friendly, curriculum-focused conversations and answer questions in a concise, approachable way. For basic and simple questions, aim to respond with one or two words, but don't be static - add a bit of humor in between the conversation. When explaining concepts, focus only on the essentials, making them easy to understand with relatable analogies and examples. Use humor to make the conversation both educational and enjoyable. For links, provide only valid, accessible websites when requested. For current events, news, or sports updates, use the Gemini tool to provide accurate, up-to-date information. Relate academic concepts to real-world observations and experiments.",
)

history=[]

print("Hello, How can I help you?")

while True:

    user_input = input("You:")

    chat_session = model.start_chat(
        history=history
  )

    response = chat_session.send_message(user_input)

    model_response = response.text
    print(f'Bot: {model_response}')
    print()

    history.append({"role": "user", "parts":[user_input]})
    history.append({"role": "model", "parts": [model_response]})
