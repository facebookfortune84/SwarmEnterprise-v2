"""
Unit tests for Lead Discovery Agent
"""
import pytest
from unittest.mock import patch, MagicMock
from agents.marketing.lead_discovery import LeadDiscoveryAgent


class TestLeadDiscovery:
    @pytest.fixture
    def discovery_agent(self):
        with patch("agents.marketing.lead_discovery.get_local_brain_instance"):
            return LeadDiscoveryAgent()

    @pytest.mark.asyncio
    async def test_run_discovery_cycle(self, discovery_agent):
        # Mock DB
        mock_db = MagicMock()
        discovery_agent.db = mock_db

        # Patch the web_search tool's run method via patching the tool itself
        mock_tool = MagicMock()
        mock_tool.run.return_value = "Some search results"

        with patch("agents.marketing.lead_discovery.web_search", mock_tool):
            count = await discovery_agent.run_discovery_cycle("test-niche")

            assert count > 0
            assert mock_db.create_lead.called


# Made with Bob
