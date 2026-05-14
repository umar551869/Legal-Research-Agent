import httpx
import json
import logging
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen3:4b", 
                 fallback_model: str = "llama3.1:8b",
                 openai_api_key: Optional[str] = None, openai_model: str = "gpt-3.5-turbo"):
        self.base_url = base_url
        self.model = model
        self.fallback_model = fallback_model
        self.openai_api_key = openai_api_key
        self.openai_model = openai_model
        self._ollama_available = None
        
    def _is_real_openai_key(self) -> bool:
        """Check if the OpenAI key is a real key, not a placeholder."""
        if not self.openai_api_key:
            return False
        placeholders = ["your_openai_api_key_here", "your-api-key", "sk-xxx", ""]
        return self.openai_api_key.strip() not in placeholders

    async def _check_ollama_availability(self) -> bool:
        """Check if Ollama is available using async httpx. Retries on each call if previously failed."""
        if self._ollama_available is True:
            return True
            
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                self._ollama_available = response.status_code == 200
                if self._ollama_available:
                    logger.info("Ollama is available")
                return self._ollama_available
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            self._ollama_available = False
            return False

    async def generate_stream(self, prompt: str, system: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        Stream completion tokens. Tries primary model first, then fallback model, then OpenAI.
        """
        if await self._check_ollama_availability():
            # Try primary model first, then fallback
            for model_name in [self.model, self.fallback_model]:
                url = f"{self.base_url}/api/generate"
                payload = {
                    "model": model_name,
                    "prompt": prompt,
                    "stream": True,
                }
                if system: payload["system"] = system

                try:
                    logger.info(f"Trying Ollama model: {model_name}")
                    got_tokens = False
                    async with httpx.AsyncClient(timeout=None) as client:
                        async with client.stream("POST", url, json=payload) as response:
                            response.raise_for_status()
                            async for line in response.aiter_lines():
                                if not line: continue
                                chunk = json.loads(line)
                                if "response" in chunk:
                                    got_tokens = True
                                    yield chunk["response"]
                                if chunk.get("done"):
                                    break
                    if got_tokens:
                        return  # Success, don't try fallback
                except Exception as e:
                    logger.warning(f"Ollama model '{model_name}' failed: {e}")
                    continue  # Try next model

            # If both models failed, mark ollama as unavailable
            self._ollama_available = False

        # Fallback to OpenAI Streaming (only if real key)
        if self._is_real_openai_key():
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=self.openai_api_key)
                
                messages = []
                if system: messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                stream = await client.chat.completions.create(
                    model=self.openai_model,
                    messages=messages,
                    stream=True
                )
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            except Exception as e:
                logger.error(f"OpenAI stream error: {e}")
                yield f"Error: {str(e)}"

    async def generate(self, prompt: str, system: Optional[str] = None, json_mode: bool = False) -> Dict[str, Any]:
        """Non-streaming generation with fallback"""
        if await self._check_ollama_availability():
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }
            if system: payload["system"] = system
            if json_mode: payload["format"] = "json"

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    result = response.json()
                    result["provider"] = "ollama"
                    return result
            except Exception as e:
                logger.error(f"Ollama error: {e}")
                self._ollama_available = False

        # OpenAI Fallback (Non-streaming)
        if not self._is_real_openai_key():
            return {"error": "No LLM provider available. Please ensure Ollama is running on localhost:11434."}
            
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.openai_api_key)
            messages = []
            if system: messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            response = await client.chat.completions.create(
                model=self.openai_model,
                messages=messages
            )
            return {
                "response": response.choices[0].message.content,
                "provider": "openai"
            }
        except Exception as e:
            return {"error": str(e)}

