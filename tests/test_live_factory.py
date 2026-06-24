"""
Integration tests for Live Swarm Components.
Verifies the end-to-end Mission -> Tickets -> Provisioning flow.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from agents.managers.commander import SwarmCommander
from backend.services.company_generator import CompanyGenerator, CompanyRequest, TechStack

class TestLiveSwarm:
    
    @pytest.fixture
    def commander(self):
        with patch('agents.managers.commander.get_local_brain_instance'):
            return SwarmCommander()

    @pytest.mark.asyncio
    async def test_end_to_end_mission_flow(self, commander):
        """Tests that a mission correctly results in tickets and a generation task."""
        mission = "Build a CRM for real estate agents"
        
        # 1. Commander Decomposes
        with patch('agents.managers.commander.strategic_board.convene', return_value=[
            {"department": "Engineering", "title": "API Design", "instruction": "Design the CRM API"}
        ]):
            res = await commander.execute_mission(mission)
            assert res["status"] == "IN_PROGRESS"
            assert res["tickets_enqueued"] == 1

        # 2. Check if tickets are in DB (using commander's db instance)
        tickets = commander.db.list_tickets(project_id=res["mission_id"])
        assert len(tickets) == 1
        assert tickets[0]["title"] == "API Design"

    @pytest.mark.asyncio
    async def test_factory_generation_logic(self):
        """Verifies the factory generator correctly handles requests."""
        generator = CompanyGenerator()
        import uuid
        unique_name = f"TestCRM-{uuid.uuid4().hex[:4]}"
        
        request = CompanyRequest(
            name=unique_name,
            description="Testing the generator",
            tech_stack=TechStack.FASTAPI_REACT_POSTGRES,
            features=["auth"],
            user_id="LIVE_TEST"
        )
        
        # Mocking the slow internal execution
        with patch.object(generator, '_execute_generation', return_value=None):
            result = await generator.generate_company(request)
            assert "company_id" in result
            assert result["status"] == "pending"

# Made with Bob
