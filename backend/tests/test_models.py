from llm_client import LLMClient

client = LLMClient()
models = client.get_available_models()
print("Available models:")
for model in models:
    print(f"  - {model}")

print(f"\nTotal models: {len(models)}")
print(f"Contains Grok: {'grok' in str(models).lower()}")
