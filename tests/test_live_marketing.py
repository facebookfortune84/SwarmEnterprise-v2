"""
Integration tests for Live Marketing and Outreach.
"""

import pytest
from unittest.mock import patch, MagicMock
from agents.marketing.lead_discovery import LeadDiscoveryAgent
from agents.outreach.worker import enqueue_outreach

class TestLiveMarketing:
    
    @pytest.fixture
    def discovery_agent(self):
        with patch('agents.marketing.lead_discovery.get_local_brain_instance'):
            return LeadDiscoveryAgent()

    @pytest.mark.asyncio
    async def test_lead_discovery_persists_leads(self, discovery_agent):
        """Verifies discovered leads are correctly added to the database."""
        # Patch the entire tool object at the module level
        mock_tool = MagicMock()
        mock_tool.run.return_value = "Search result data"
        
        with patch('agents.marketing.lead_discovery.web_search', mock_tool):
            # Mock extraction logic to return predictable data
            discovery_agent._analyze_search_results = lambda x: [
                {"company": "TestLead", "name": "Test Person", "email": "test@lead.com"}
            ]
            
            count = await discovery_agent.run_discovery_cycle("test-niche")
            assert count == 1
            
            # Verify in DB
            leads = discovery_agent.db.list_leads(limit=10)
            assert any(l["email"] == "test@lead.com" for l in leads)

    def test_outreach_queueing(self):
        """Verifies outreach tasks can be enqueued for the worker."""
        with patch('backend.queue.enqueue_task') as mock_enqueue:
            enqueue_outreach("prospect@example.com", "Hello", "Interesting offer")
            assert mock_enqueue.called
            payload = mock_enqueue.call_args[0][0]
            assert payload["to_email"] == "prospect@example.com"
            assert payload["subject"] == "Hello"

# Made with Bob
