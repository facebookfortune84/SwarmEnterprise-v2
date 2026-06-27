"""
Web Search Tool - Allows agents to search the internet for leads and information.
"""

import os
import logging
from langchain.tools import tool

logger = logging.getLogger("WebSearchTool")


@tool("web_search")
def web_search(query: str) -> str:
    """
    Search the internet for a query.
    Useful for lead discovery and market research.
    """
    # Try to use SerpApi if key is present
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if serpapi_key:
        try:
            from langchain_community.utilities import SerpAPIWrapper

            search = SerpAPIWrapper(serpapi_key=serpapi_key)
            return search.run(query)
        except Exception as e:
            logger.error(f"SerpApi failed: {e}")

    # Fallback to DuckDuckGo (free, no key needed)
    try:
        from langchain_community.tools import DuckDuckGoSearchRun

        search = DuckDuckGoSearchRun()
        return search.run(query)
    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        return f"ERROR: Could not perform search for '{query}'. No search providers available."


@tool("extract_leads_from_text")
def extract_leads_from_text(text: str) -> str:
    """
    Parses raw text to identify potential leads (emails, company names).
    Returns a JSON string of identified leads.
    """
    # This would typically use an LLM to parse, but for the tool definition,
    # we'll keep it as a placeholder that the agent can use with its own logic.
    return "Please process this text with your LLM to extract JSON leads: [Name, Email, Company, Pain Point]"
