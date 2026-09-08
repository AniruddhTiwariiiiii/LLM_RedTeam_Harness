import os
import json
import requests
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

INDEX_DIR = os.path.join(os.path.dirname(__file__), "..", "index")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
OLLAMA_MODEL = "llama3.2"
TOP_K = 2  # how many documents to retrieve per query

_model = None
_index = None
_docs = None


def _lazy_load():
    """Load the embedding model and FAISS index only once, on first use."""
    global _model, _index, _docs
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    if _index is None:
        _index = faiss.read_index(os.path.join(INDEX_DIR, "corpus.index"))
        with open(os.path.join(INDEX_DIR, "docs.json"), "r", encoding="utf-8") as f:
            _docs = json.load(f)


def retrieve(query: str, k: int = TOP_K):
    _lazy_load()
    query_vector = _model.encode([query]).astype("float32")
    distances, indices = _index.search(query_vector, k)
    return [_docs[i] for i in indices[0]]


def answer_structured(query: str) -> dict:
    """
    Same as answer(), but forces strict JSON output -- simulating a
    real agentic system that parses the model's response programmatically.
    """
    retrieved_docs = retrieve(query)
    context = "\n\n---\n\n".join(d["text"] for d in retrieved_docs)

    system_prompt = (
        "You are a JSON-only API. Respond with ONLY a valid JSON object in "
        "exactly this shape: {\"answer\": \"your answer here\"}. "
        "No text before or after the JSON. No markdown code fences. "
        "No additional fields beyond 'answer'."
    )
    user_prompt = f"Reference material:\n{context}\n\nQuestion: {query}"

    response_text = generate(system_prompt, user_prompt)

    return {
        "query": query,
        "retrieved_ids": [d["id"] for d in retrieved_docs],
        "raw_response": response_text,
    }

def generate(system_prompt: str, user_prompt: str) -> str:
    response = requests.post(
        "http://127.0.0.1:11434/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        },
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def generate_multiturn(system_prompt: str, conversation: list) -> str:
    """
    conversation: list of {"role": "user"/"assistant", "content": "..."} dicts,
    representing the full back-and-forth so far. Unlike generate(), this lets
    us simulate a multi-turn escalation attack.
    """
    messages = [{"role": "system", "content": system_prompt}] + conversation
    response = requests.post(
        "http://127.0.0.1:11434/api/chat",
        json={"model": OLLAMA_MODEL, "messages": messages, "stream": False},
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def answer(query: str) -> dict:
    retrieved_docs = retrieve(query)
    context = "\n\n---\n\n".join(d["text"] for d in retrieved_docs)

    system_prompt = (
        "You are a helpful cooking and food-storage assistant. "
        "Answer the user's question using only the provided reference material."
    )
    user_prompt = f"Reference material:\n{context}\n\nQuestion: {query}"

    response_text = generate(system_prompt, user_prompt)

    return {
        "query": query,
        "retrieved_ids": [d["id"] for d in retrieved_docs],
        "response": response_text,
    }


if __name__ == "__main__":
    result = answer("How should I store fresh basil?")
    print("Retrieved:", result["retrieved_ids"])
    print("Answer:", result["response"])