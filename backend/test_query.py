import requests
import json

# Test the bot query endpoint
url = "http://localhost:8000/bots/eeebbb60-e9eb-4250-be5c-affe0809fba8/query/"
data = {
    "prompt": "What is CSR?",
    "llm_model": "deepseek/deepseek-r1-0528-qwen3-8b:free",
    "top_k": 5
}

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")