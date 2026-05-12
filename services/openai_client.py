import os

import requests
from dotenv import load_dotenv


load_dotenv()


def _get_api_key():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "your_api_key_here":
        raise ValueError(
            "Set OPENAI_API_KEY in .env before calling the chatbot or embedder."
        )
    return api_key


class OpenAIEmbeddingsClient:
    def __init__(self, model="text-embedding-3-small"):
        self.model = model

    def _embed(self, input_texts):
        response = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {_get_api_key()}",
                "Content-Type": "application/json",
            },
            json={"model": self.model, "input": input_texts},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()["data"]
        return [item["embedding"] for item in data]

    def embed_documents(self, texts):
        return self._embed(texts)

    def embed_query(self, text):
        return self._embed([text])[0]


def chat_completion(messages, model="gpt-4o-mini", temperature=0):
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {_get_api_key()}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "temperature": temperature,
            "messages": messages,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]