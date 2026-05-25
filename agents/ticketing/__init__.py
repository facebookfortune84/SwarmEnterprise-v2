"""
Autonomous Ticketing Agent Team

Autonomous ticket management agents:
- Linear/GitHub integration
- Ticket prioritizer
- Backlog manager
"""

from .linear_integration import LinearIntegration
from .ticket_prioritizer import TicketPrioritizer
from .backlog_manager import BacklogManager

__all__ = [
    "LinearIntegration",
    "TicketPrioritizer",
    "BacklogManager",
]

# Made with Bob
