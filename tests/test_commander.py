"""
Unit tests for Swarm Commander
"""
import pytest
from unittest.mock import patch, MagicMock
from agents.managers.commander import SwarmCommander

class TestSwarmCommander:
    @pytest.fixture
    def commander(self):
        with patch('agents.managers.commander.get_local_brain_instance'):
            return SwarmCommander()

    @pytest.mark.asyncio
    async def test_execute_mission_enqueues_tickets(self, commander):
        mission = "Build a revolutionary AI app"
        
        # Mock DB and Board
        mock_db = MagicMock()
        mock_ticket = MagicMock()
        mock_ticket.id = "T1"
        mock_db.create_ticket.return_value = mock_ticket
        commander.db = mock_db
        
        with patch('agents.managers.commander.strategic_board.convene', return_value=[
            {"department": "Engineering", "title": "Setup", "instruction": "Do it"}
        ]):
            result = await commander.execute_mission(mission)
            
            assert result["status"] == "IN_PROGRESS"
            assert result["tickets_enqueued"] == 1
            assert mock_db.create_ticket.called

# Made with Bob
