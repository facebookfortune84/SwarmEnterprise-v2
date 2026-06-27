"""
Lead Discovery Agent - Autonomously identifies and extracts potential customers.
Follows LEAD_EXTRACTION.md SOP.
"""

import json
import logging
import re
from typing import List, Dict, Any

from agents.llm_config import get_local_brain_instance
from agents.asset_manager import asset_manager
from agents.tools.web_search import web_search
from backend.db.linear_engine import get_swarm_db

logger = logging.getLogger("LeadDiscoveryAgent")


class LeadDiscoveryAgent:
    """
    Autonomous agent for finding new customers without an initial list.
    Uses web search and LLM analysis to identify high-intent targets.
    """

    def __init__(self):
        try:
            from crewai import Agent
        except ImportError:
            # Fallback/Mock for environment compatibility
            self.agent = None
            logger.warning("crewai not installed. Agent functionality will be limited.")
            return

        brain = get_local_brain_instance()

        # Load SOP and specialized prompt from assets
        sop = asset_manager.get_sop("LEAD_EXTRACTION")
        system_prompt = asset_manager.get_prompt("Enterprise Prompt")

        self.agent = Agent(
            role="Lead Generation Specialist",
            goal="Identify 50+ high-value B2B leads per week who need autonomous factory solutions.",
            backstory=f"""You are an expert at digital OSINT and market research. 
            You follow this SOP: {sop[:500]}...
            You are powered by the SwarmEnterprise core: {system_prompt[:200]}...""",
            llm=brain,
            tools=[web_search],
            verbose=True,
        )
        self.db = get_swarm_db()

    async def run_discovery_cycle(self, niche: str = "SaaS startups needing automation"):
        """
        Execute one discovery cycle for a specific niche.
        """
        logger.info(f"Starting lead discovery cycle for: {niche}")

        if not self.agent:
            logger.error("Agent not initialized. Cannot run discovery.")
            return

        # 1. Search for targets
        query = f"recent Y Combinator startups or funded SaaS companies in {niche}"
        search_results = web_search(query)

        # 2. Analyze and extract (Simulated agent task here)
        # In a real CrewAI setup, this would be a Task
        extracted_leads = self._analyze_search_results(search_results)

        # 3. Persist to DB
        count = 0
        for lead in extracted_leads:
            try:
                self.db.create_lead(
                    email=str(
                        lead.get(
                            "email", "info@" + str(lead.get("company", "unknown")).lower() + ".com"
                        )
                    ),
                    name=str(lead.get("name", "")),
                    company=str(lead.get("company", "")),
                    metadata=lead,
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to save lead {lead}: {e}")

        logger.info(f"Discovery cycle complete. Added {count} leads.")
        return count

    # Hardcoded mock used only when LLM is completely unavailable
    _MOCK_LEADS = [
        {
            "company": "NexusAI",
            "name": "Sarah Chen",
            "email": "sarah@nexusai.io",
            "niche": "Automation",
        },
        {
            "company": "VortexSystems",
            "name": "Marcus Thorne",
            "email": "m.thorne@vortex.com",
            "niche": "DevOps",
        },
        {
            "company": "CloudPulse",
            "name": "Elena Rodriguez",
            "email": "elena@cloudpulse.tech",
            "niche": "SaaS",
        },
    ]

    def _analyze_search_results(self, results: str) -> List[Dict[str, Any]]:
        """
        Use the local LLM to extract company names, contact names, and emails from
        raw web-search results.  Falls back to the hardcoded mock if the LLM is
        unavailable or returns unparseable output.
        """
        brain = get_local_brain_instance()
        if brain is None:
            logger.warning("LLM not available; returning mock leads")
            return self._MOCK_LEADS

        prompt = (
            "You are a lead extraction specialist. "
            "Given the following web search results, extract all B2B company leads.\n"
            "For each lead output a JSON object with keys: company, name, email, niche.\n"
            "Return a JSON array only — no explanation, no markdown fences.\n\n"
            f"SEARCH RESULTS:\n{results[:4000]}\n\n"
            "JSON array of leads:"
        )

        try:
            # brain is a LangChain Ollama LLM; call it as a string -> string function
            raw = brain(prompt) if callable(brain) else str(brain)
        except Exception as e:
            logger.error(f"LLM invocation failed during lead analysis: {e}")
            return self._MOCK_LEADS

        # Attempt to parse the JSON from the LLM response
        leads = self._parse_leads_json(raw)
        if leads is not None:
            return leads

        logger.warning("LLM returned non-JSON lead output; falling back to mock")
        return self._MOCK_LEADS

    @staticmethod
    def _parse_leads_json(raw: str) -> List[Dict[str, Any]] | None:
        """
        Try multiple strategies to extract a JSON array from an LLM response.
        Returns None if no valid array is found.
        """
        raw = raw.strip()

        # Strategy 1: direct parse
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 2: strip markdown code fences (```json ... ```)
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if fence_match:
            try:
                parsed = json.loads(fence_match.group(1).strip())
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

        # Strategy 3: find first [...] array in text
        bracket_match = re.search(r"(\[\s*\{.*?\}\s*\])", raw, re.DOTALL)
        if bracket_match:
            try:
                parsed = json.loads(bracket_match.group(1))
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

        return None


# Global instance
lead_discovery_agent = LeadDiscoveryAgent()
