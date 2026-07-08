"""
Ollama LLM Client (Intelligence-Enabled)
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# ============================================================
# ✅ INTELLIGENCE LAYER (SAFE LOAD)
# ============================================================

INTELLIGENCE_ENABLED = False
intel: Any = None

try:
    from backend.intelligence.runtime import Intelligence

    intel = Intelligence()
    INTELLIGENCE_ENABLED = True
    logger.info("✅ Intelligence layer loaded")

except Exception as e:
    logger.warning(f"⚠️ Intelligence disabled: {e}")


# ============================================================
# ✅ CONFIG
# ============================================================

@dataclass
class OllamaConfig:
    base_url: str
    model: str
    timeout: int = 120
    max_retries: int = 3
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40


# ============================================================
# ✅ CLIENT
# ============================================================

class OllamaClient:

    def __init__(self, config: Optional[OllamaConfig] = None):

        if config is None:
            config = OllamaConfig(
                base_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
                model=os.getenv("OLLAMA_MODEL", "qwen2.5-coder:latest"),
                timeout=int(os.getenv("OLLAMA_TIMEOUT", "120")),
                temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
            )

        self.config = config

        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout
        )

        logger.info(f"Ollama client initialized ({config.model})")

    async def close(self):
        await self.client.aclose()

    # ============================================================
    # ✅ INTELLIGENCE WRAPPER
    # ============================================================

    def _apply_intelligence(self, prompt, system):

        if not INTELLIGENCE_ENABLED or not prompt:
            return prompt, system

        try:
            ctx = intel.build_context(prompt)

            logger.info(f"[INTEL] archetype={ctx['archetype']}")

            new_system = f"""
You are acting as a {ctx['archetype']} agent.

Execution Chain:
{" -> ".join(ctx["chain"])}

Use the following system knowledge:

{ctx["context"]}

Respond clearly and structured.
"""

            if system:
                new_system += f"\n\nAdditional Instructions:\n{system}"

            return prompt, new_system

        except Exception as e:
            logger.warning(f"[INTEL FAIL] {e}")
            return prompt, system

    # ============================================================
    # ✅ GENERATE
    # ============================================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=2, max=10),
        reraise=True
    )
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
    ) -> str:

        try:
            prompt, system = self._apply_intelligence(prompt, system)

            payload = {
                "model": self.config.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature or self.config.temperature,
                    "top_p": self.config.top_p,
                    "top_k": self.config.top_k,
                }
            }

            if system:
                payload["system"] = system

            if max_tokens:
                payload["options"]["num_predict"] = max_tokens

            if stop:
                payload["options"]["stop"] = stop

            res = await self.client.post("/api/generate", json=payload)
            res.raise_for_status()

            return res.json().get("response", "")

        except Exception as e:
            logger.error(f"Generate error: {e}")
            raise

    # ============================================================
    # ✅ STREAM
    # ============================================================

    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> AsyncIterator[str]:
        try:
            prompt, system = self._apply_intelligence(prompt, system)

            payload = {
                "model": self.config.model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature or self.config.temperature,
                    "top_p": self.config.top_p,
                    "top_k": self.config.top_k,
                }
            }

            if system:
                payload["system"] = system

            async with self.client.stream(
                "POST",
                "/api/generate",
                json=payload
            ) as response:

                response.raise_for_status()

                async for line in response.aiter_lines():

                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                    except:
                        continue

        except Exception as e:
            logger.error(f"Stream error: {e}")
            raise

    # ============================================================
    # ✅ CHAT
    # ============================================================

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:

        try:
            if INTELLIGENCE_ENABLED and messages:
                try:
                    user_msg = messages[-1]["content"]
                    ctx = intel.build_context(user_msg)

                    messages.insert(0, {
                        "role": "system",
                        "content": f"""
You are a {ctx['archetype']} agent.

Execution Chain:
{" -> ".join(ctx["chain"])}

System knowledge:
{ctx["context"]}
"""
                    })

                    logger.info(f"[CHAT INTEL] {ctx['archetype']}")

                except Exception as e:
                    logger.warning(f"[CHAT INTEL FAIL] {e}")

            payload = {
                "model": self.config.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature or self.config.temperature,
                    "top_p": self.config.top_p,
                    "top_k": self.config.top_k,
                }
            }

            if max_tokens:
                payload["options"]["num_predict"] = max_tokens

            res = await self.client.post("/api/chat", json=payload)
            res.raise_for_status()

            return res.json().get("message", {}).get("content", "")

        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise

    # ============================================================
    # ✅ UTILS
    # ============================================================

    async def health_check(self) -> bool:
        try:
            res = await self.client.get("/")
            return res.status_code == 200
        except:
            return False

    async def list_models(self):
        res = await self.client.get("/api/tags")
        return res.json().get("models", [])