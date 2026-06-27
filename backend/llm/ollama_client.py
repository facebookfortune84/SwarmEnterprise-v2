"""
Ollama LLM Client - Free, Self-Hosted LLM Integration

Connects to Ollama server running on your laptop for zero-cost AI inference.
Supports streaming, embeddings, and multiple models.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@dataclass
class OllamaConfig:
    """Ollama configuration"""

    base_url: str
    model: str
    timeout: int = 120
    max_retries: int = 3
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40


class OllamaClient:
    """
    Client for interacting with Ollama LLM server.

    Ollama is a free, open-source LLM runtime that runs models locally.
    Perfect for self-hosted, zero-cost AI inference.

    Supported models:
    - llama3 (8B, 70B)
    - codellama (7B, 13B, 34B)
    - mistral (7B)
    - mixtral (8x7B)
    - phi-2 (2.7B)
    - neural-chat (7B)
    """

    def __init__(self, config: Optional[OllamaConfig] = None):
        """
        Initialize Ollama client.

        Args:
            config: Ollama configuration. If None, loads from environment.
        """
        if config is None:
            config = OllamaConfig(
                base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
                model=os.getenv("OLLAMA_MODEL", "llama3"),
                timeout=int(os.getenv("OLLAMA_TIMEOUT", "120")),
                temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
            )

        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout,
        )

        logger.info(f"Initialized Ollama client: {config.base_url} (model: {config.model})")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True
    )
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
    ) -> str:
        """
        Generate text completion.

        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            stop: Stop sequences

        Returns:
            Generated text
        """
        try:
            payload = {
                "model": self.config.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature or self.config.temperature,
                    "top_p": self.config.top_p,
                    "top_k": self.config.top_k,
                },
            }

            if system:
                payload["system"] = system

            if max_tokens:
                payload["options"]["num_predict"] = max_tokens

            if stop:
                payload["options"]["stop"] = stop

            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()

            result = response.json()
            return result["response"]

        except httpx.HTTPError as e:
            logger.error(f"Ollama HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AsyncIterator[str]:
        """
        Generate text completion with streaming.

        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Sampling temperature

        Yields:
            Text chunks as they are generated
        """
        try:
            payload = {
                "model": self.config.model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature or self.config.temperature,
                    "top_p": self.config.top_p,
                    "top_k": self.config.top_k,
                },
            }

            if system:
                payload["system"] = system

            async with self.client.stream("POST", "/api/generate", json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPError as e:
            logger.error(f"Ollama streaming error: {e}")
            raise

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Chat completion (multi-turn conversation).

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Assistant's response
        """
        try:
            payload = {
                "model": self.config.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature or self.config.temperature,
                    "top_p": self.config.top_p,
                    "top_k": self.config.top_k,
                },
            }

            if max_tokens:
                payload["options"]["num_predict"] = max_tokens

            response = await self.client.post("/api/chat", json=payload)
            response.raise_for_status()

            result = response.json()
            return result["message"]["content"]

        except httpx.HTTPError as e:
            logger.error(f"Ollama chat error: {e}")
            raise

    async def embeddings(self, text: str) -> List[float]:
        """
        Generate embeddings for text.

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        try:
            payload = {
                "model": self.config.model,
                "prompt": text,
            }

            response = await self.client.post("/api/embeddings", json=payload)
            response.raise_for_status()

            result = response.json()
            return result["embedding"]

        except httpx.HTTPError as e:
            logger.error(f"Ollama embeddings error: {e}")
            raise

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models.

        Returns:
            List of model information dicts
        """
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()

            result = response.json()
            return result.get("models", [])

        except httpx.HTTPError as e:
            logger.error(f"Ollama list models error: {e}")
            raise

    async def pull_model(self, model_name: str) -> bool:
        """
        Pull a model from Ollama library.

        Args:
            model_name: Name of model to pull (e.g., "llama3", "codellama")

        Returns:
            True if successful
        """
        try:
            payload = {"name": model_name}

            response = await self.client.post("/api/pull", json=payload)
            response.raise_for_status()

            logger.info(f"Successfully pulled model: {model_name}")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Ollama pull model error: {e}")
            return False

    async def health_check(self) -> bool:
        """
        Check if Ollama server is healthy.

        Returns:
            True if server is responding
        """
        try:
            response = await self.client.get("/")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def get_model_info(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about a model.

        Args:
            model_name: Model name (defaults to configured model)

        Returns:
            Model information dict
        """
        try:
            model = model_name or self.config.model
            payload = {"name": model}

            response = await self.client.post("/api/show", json=payload)
            response.raise_for_status()

            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Ollama model info error: {e}")
            raise


# Convenience functions for common use cases


async def generate_code(
    prompt: str, language: str = "python", client: Optional[OllamaClient] = None
) -> str:
    """
    Generate code using CodeLlama model.

    Args:
        prompt: Code generation prompt
        language: Programming language
        client: Ollama client (creates new if None)

    Returns:
        Generated code
    """
    if client is None:
        config = OllamaConfig(
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            model="codellama",
        )
        client = OllamaClient(config)

    system_prompt = (
        f"You are an expert {language} programmer. Generate clean, efficient, well-documented code."
    )

    try:
        return await client.generate(prompt, system=system_prompt)
    finally:
        if client:
            await client.close()


async def analyze_code(
    code: str, task: str = "review", client: Optional[OllamaClient] = None
) -> str:
    """
    Analyze code for issues, improvements, or documentation.

    Args:
        code: Code to analyze
        task: Analysis task (review, document, optimize, security)
        client: Ollama client

    Returns:
        Analysis results
    """
    if client is None:
        config = OllamaConfig(
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            model="codellama",
        )
        client = OllamaClient(config)

    task_prompts = {
        "review": "Review this code for bugs, issues, and improvements:",
        "document": "Generate comprehensive documentation for this code:",
        "optimize": "Suggest optimizations for this code:",
        "security": "Analyze this code for security vulnerabilities:",
    }

    prompt = f"{task_prompts.get(task, task_prompts['review'])}\n\n```\n{code}\n```"

    try:
        return await client.generate(prompt)
    finally:
        if client:
            await client.close()


async def generate_tests(
    code: str, framework: str = "pytest", client: Optional[OllamaClient] = None
) -> str:
    """
    Generate unit tests for code.

    Args:
        code: Code to test
        framework: Testing framework (pytest, unittest, jest)
        client: Ollama client

    Returns:
        Generated test code
    """
    if client is None:
        config = OllamaConfig(
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            model="codellama",
        )
        client = OllamaClient(config)

    prompt = f"Generate comprehensive {framework} tests for this code:\n\n```\n{code}\n```"

    try:
        return await client.generate(prompt)
    finally:
        if client:
            await client.close()


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Initialize client
        client = OllamaClient()

        # Check health
        healthy = await client.health_check()
        print(f"Ollama server healthy: {healthy}")

        # List models
        models = await client.list_models()
        print(f"Available models: {[m['name'] for m in models]}")

        # Generate text
        response = await client.generate(
            prompt="Write a Python function to calculate fibonacci numbers",
            system="You are a helpful coding assistant",
        )
        print(f"Response: {response}")

        # Chat
        messages = [
            {"role": "user", "content": "What is Python?"},
        ]
        chat_response = await client.chat(messages)
        print(f"Chat response: {chat_response}")

        await client.close()

    asyncio.run(main())

# Made with Bob
