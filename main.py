from fastapi import FastAPI
from services.chatbot import load_chatbot
from routes.auth import authrouter

app = FastAPI()

app.include_router(authrouter)

@app.get("/ask")
def ask_question(query: str, role: str):
    
    qa_bot = load_chatbot(role)

    response = qa_bot.invoke(query)

    return {
        "answer": response["result"]
    }
