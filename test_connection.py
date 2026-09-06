import requests

response = requests.post(
    "http://127.0.0.1:11434/api/chat",
    json={
        "model": "llama3.2",
        "messages": [
            {"role": "user", "content": "Say 'connection successful' and nothing else."}
        ],
        "stream": False
    }
)

response.raise_for_status()  
data = response.json()
print(data["message"]["content"])