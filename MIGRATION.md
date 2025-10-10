# Migration from Ollama to OpenRouter

We have migrated from using local Ollama models to OpenRouter's free tier models. This provides several benefits:

1. No need to run a local model server
2. Access to high-quality hosted models
3. More consistent performance
4. No large model downloads required

## Available Free Models

We now use the following free models from OpenRouter:

1. Qwen3 Coder (480B) - Best for code generation
2. DeepSeek V3.1 (671B) - Great for reasoning
3. GLM 4.5 Air - Balanced general purpose
4. Tongyi DeepResearch 30B - Research focused
5. Nemotron Nano 9B V2 - Fast and efficient

## Setup

1. Get an API key from [OpenRouter](https://openrouter.ai)
2. Add it to your `.env` file:
```bash
OPENROUTER_API_KEY=your_api_key_here
```

## Changes from Previous Version

- Removed Ollama dependency
- Updated model selection UI
- Added OpenRouter client
- Improved response handling
- Better error handling and rate limiting

Please update your local installations accordingly.