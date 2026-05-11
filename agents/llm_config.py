import os
import logging
from langchain_community.llms import Ollama

logger = logging.getLogger("SwarmBrain")

class NetworkBridge:
    """Discovers Ollama at resolved Windows IP via socat proxy"""
    
    @staticmethod
    def discover_ollama_url():
        # Priority 1: Environment variable
        if os.getenv("OLLAMA_URL"):
            url = os.getenv("OLLAMA_URL")
            logger.info(f"Using OLLAMA_URL from env: {url}")
            return url
        
        # Priority 2: Try localhost (socat proxy running)
        localhost_url = "http://localhost:11434"
        logger.info(f"Testing socat proxy at: {localhost_url}")
        
        try:
            import requests
            response = requests.get(f"{localhost_url}/api/tags", timeout=3)
            if response.status_code == 200:
                logger.info(f"✅ Ollama found via socat proxy: {localhost_url}")
                return localhost_url
        except Exception as e:
            logger.warning(f"Socat proxy unreachable: {e}")
        
        # Priority 3: Try resolved Windows IP directly
        windows_url = "http://172.29.192.1:11434"
        logger.info(f"Testing Windows IP directly: {windows_url}")
        
        try:
            import requests
            response = requests.get(f"{windows_url}/api/tags", timeout=3)
            if response.status_code == 200:
                logger.info(f"✅ Ollama found at Windows IP: {windows_url}")
                return windows_url
        except Exception as e:
            logger.warning(f"Windows IP unreachable: {e}")
        
        # Fallback
        logger.error(f"❌ Could not reach Ollama. Using fallback: {localhost_url}")
        return localhost_url

class SwarmBrain:
    """FOSS Sovereign LLM Controller"""
    
    @staticmethod
    def get_local_brain(model_name="llama3.2:3b"):
        ollama_url = NetworkBridge.discover_ollama_url()
        logger.info(f"Initializing OllamaLLM: {model_name} @ {ollama_url}")
        
        return Ollama(
            model=model_name,
            base_url=ollama_url,
            temperature=0.1,
            top_k=10,
            top_p=0.9,
            num_ctx=4096
        )
    
    @staticmethod
    def get_embedder():
        ollama_url = NetworkBridge.discover_ollama_url()
        return {
            "provider": "ollama",
            "config": {
                "model": "nomic-embed-text:latest",
                "base_url": ollama_url
            }
        }

LOCAL_BRAIN = SwarmBrain.get_local_brain()
EMBEDDER = SwarmBrain.get_embedder()

logger.info("✅ SwarmBrain initialized with Ollama")