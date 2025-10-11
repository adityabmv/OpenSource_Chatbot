import asyncio
from llm_client import LLMClient

async def test_api():
    client = LLMClient()
    is_valid = await client.validate_api_key()
    print(f"API Key valid: {is_valid}")

    # Try a simple chat message if key is valid
    if is_valid:
        try:
            # Test with Grok model
            response = await client.chat([
                {"role": "user", "content": "Say hello"}
            ], model="xai-org/grok-beta")
            print(f"Grok Chat response: {response}")
        except Exception as e:
            print(f"Error in Grok chat: {e}")
        
        try:
            # Test with default model
            response = await client.chat([
                {"role": "user", "content": "Say hello"}
            ], model="deepseek/deepseek-r1-0528-qwen3-8b:free")
            print(f"DeepSeek Chat response: {response}")
        except Exception as e:
            print(f"Error in DeepSeek chat: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())