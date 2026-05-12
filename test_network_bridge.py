#!/usr/bin/env python3
"""
Test network bridge connectivity to Ollama
Run: python test_network_bridge.py
"""

import sys
import requests
import logging
from agents.llm_config import NetworkBridge, get_local_brain_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BridgeTester")

def test_ollama_connection():
    """Test if we can reach Ollama"""
    logger.info("🔍 Testing Ollama connectivity...")
    
    url = NetworkBridge.discover_ollama_url()
    logger.info(f"Discovered URL: {url}")
    
    try:
        # Test /api/tags endpoint
        response = requests.get(f"{url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            logger.info(f"✅ Ollama is reachable!")
            logger.info(f"   Available models: {len(models)}")
            for model in models[:5]:
                logger.info(f"   - {model.get('name')}")
            return True
        else:
            logger.error(f"❌ Ollama responded with status {response.status_code}")
            return False
    except requests.ConnectionError as e:
        logger.error(f"❌ Cannot connect to Ollama: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing Ollama: {e}")
        return False

def test_llm_inference():
    """Test if we can actually run inference"""
    logger.info("\n🧠 Testing LLM inference...")
    
    try:
        brain = get_local_brain_instance()
        if brain is None:
            logger.warning("No local brain available; skipping LLM inference test.")
            return False
        # Call whatever interface the brain provides; trying .invoke or .generate
        if hasattr(brain, 'invoke'):
            response = brain.invoke("Say 'hello world' in JSON format: {\"message\": \"...\"}. Return ONLY valid JSON.")
        elif hasattr(brain, 'generate'):
            response = brain.generate("Say 'hello world' in JSON format: {\"message\": \"...\"}. Return ONLY valid JSON.")
        else:
            logger.warning("Local brain instance does not support invoke/generate API; skipping.")
            return False

        logger.info(f"✅ LLM responded!")
        logger.info(f"   Response: {str(response)[:200]}...")
        return True
    except Exception as e:
        logger.error(f"❌ LLM inference failed: {e}")
        return False

def test_assets():
    """Test if assets are loaded"""
    logger.info("\n📦 Testing Asset loading...")
    
    try:
        from agents.asset_manager import get_oracle_assets
        ORACLE = get_oracle_assets()
        logger.info(f"✅ Assets loaded!")
        logger.info(f"   Prompts: {len(ORACLE.prompts)}")
        logger.info(f"   SOPs: {len(ORACLE.sops)}")
        logger.info(f"   Tools: {len(ORACLE.tools)}")
        
        # Test role-specific context
        context = ORACLE.build_agent_context("CTO")
        has_prompt = bool(context['prompt'])
        has_sops = len(context['sops']) > 0
        logger.info(f"   CTO context - Prompt: {has_prompt}, SOPs: {has_sops}")
        return True
    except Exception as e:
        logger.error(f"❌ Asset loading failed: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("SWARMEOS NETWORK BRIDGE DIAGNOSTIC")
    print("="*60 + "\n")
    
    results = {
        "Ollama Connection": test_ollama_connection(),
        "LLM Inference": test_llm_inference(),
        "Asset Loading": test_assets()
    }
    
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print("="*60)
    
    if all_passed:
        print("\n🚀 ALL SYSTEMS OPERATIONAL!")
        sys.exit(0)
    else:
        print("\n⚠️  SOME SYSTEMS FAILED - See above for details")
        sys.exit(1)