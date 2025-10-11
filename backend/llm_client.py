import os
import time
from typing import List, Dict, Optional
from dotenv import load_dotenv
import httpx
import json
from datetime import datetime, timedelta

load_dotenv()

class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        # Get model from env or use default, validate it's in available models
        env_model = os.getenv("DEFAULT_MODEL")
        available_models = [
            "deepseek/deepseek-r1-0528-qwen3-8b:free",
            "qwen/qwen3-coder",
            "deepseek/deepseek-chat-v3.1",
            "z-ai/glm-4.5-air",
            "google/gemma-3-4b-it:free",
            "nousresearch/nous-hermes-2-mixtral-8x7b-dpo",
            "mistralai/mistral-7b-instruct-4k"
        ]
        self.default_model = env_model if env_model in available_models else "deepseek/deepseek-r1-0528-qwen3-8b:free"
        
        # Rate limiting
        self.requests = []
        self.max_requests_per_minute = 50  # Adjust based on your needs
        self.request_window = 60  # 1 minute window
        
    async def validate_api_key(self) -> bool:
        """Validate that the API key is working"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/anrd30/OpenSource_Chatbot",
                "X-Title": "OS_chatbot"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/auth/key",
                    headers=headers
                )
                print(f"Response status: {response.status_code}")
                print(f"Response content: {response.text}")
                return response.status_code == 200
        except Exception as e:
            print(f"API key validation failed: {e}")
            return False

    async def chat(self, messages: List[Dict[str, str]], model: str = None, api_key_override: Optional[str] = None) -> str:
        """
        Send a chat request to OpenRouter API
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: Optional model override
        
        Returns:
            The response text from the model
        """
        # No model validation: allow any model name, let OpenRouter API handle errors
        requested_model = model or self.default_model
        
        # Rate limiting check
        now = time.time()
        self.requests = [req_time for req_time in self.requests if now - req_time < self.request_window]
        if len(self.requests) >= self.max_requests_per_minute:
            raise Exception("Rate limit exceeded. Please try again later.")
        self.requests.append(now)

        api_key = api_key_override if api_key_override else None
        if not api_key:
            raise Exception("OpenRouter API key is required for chat requests.")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/anrd30/OpenSource_Chatbot",  # Your repository
            "X-Title": "OS_chatbot",  # Your application name
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": requested_model,
            "messages": messages
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )

            try:
                response.raise_for_status()  # This will raise HTTPStatusError for non-200 responses
                data = response.json()

                # Handle the response format from OpenRouter API
                if not data.get("choices"):
                    error_msg = data.get("error", {}).get("message", "No choices in response")
                    raise Exception(f"OpenRouter API error: {error_msg}")
                    
                message = data["choices"][0].get("message", {})
                if "content" in message:
                    return message["content"]
                elif "text" in message:
                    return message["text"]
                
                error_msg = data.get("error", {}).get("message", "Response missing content")
                raise Exception(f"Invalid response format: {error_msg}")
            except httpx.HTTPStatusError as e:
                raise Exception(f"OpenRouter API error (Status {response.status_code}): {response.text}")
            except json.JSONDecodeError:
                raise Exception("Invalid JSON response from OpenRouter API")
            except Exception as e:
                # Try to print parsed data if available, otherwise print raw response text
                try:
                    print(f"Response data: {json.dumps(data, indent=2)}")
                except Exception:
                    print(f"Response text: {getattr(response, 'text', '<no response>')}")
                raise Exception(f"Error parsing response: {str(e)}")

    def get_available_models(self) -> List[str]:
        """Get list of available free models"""
        return [
            # Top free models from OpenRouter (DeepSeek only):
            "deepseek/deepseek-r1-0528-qwen3-8b:free",  # Our default model
            "deepseek/deepseek-chat-v3.1",  # Great for reasoning tasks
            # Other models (non-Grok):
            "qwen/qwen3-coder",  # Best for coding tasks
            "z-ai/glm-4.5-air",  # Good general purpose model
            "nvidia/nemotron-nano-9b-v2",  # Efficient for basic tasks
            "nousresearch/nous-hermes-2-mixtral-8x7b-dpo",  # Strong overall performer
            "mistralai/mistral-7b-instruct-4k"  # Efficient instruction-following
        ]