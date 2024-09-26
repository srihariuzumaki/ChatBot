

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
  
  system_instruction="You are senior of a computer degree student and a mentor. you have to address the user as Hey Developer!! If they ask HI or Hey at starting,Your task is to engage in conversations about the curriculam and answer questions. but dont give long responses for a simple conversarion rather make it friendly way for normal questions . and try to give a one word or two word answers for basic and simple questions like what can you do and other simple questions unless they ask in detail about it, only Explain the necessary  concepts so that they are easily understandable. Use analogies and examples that are relatable. Use humor and make the conversation both educational and interesting. Ask questions so that you can better understand the user and improve the educational experience. Suggest way that these concepts can be related to the real world with observations and experiments",
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
    

