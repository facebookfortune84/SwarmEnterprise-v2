"""
Ticket Prioritizer Agent

Analyzes tickets and assigns priority scores based on multiple factors:
- Business impact
- Technical complexity
- Dependencies
- User sentiment
- Historical patterns
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
import re

from backend.llm.ollama_client import OllamaClient


logger = logging.getLogger(__name__)


class PriorityLevel(Enum):
    """Priority levels for tickets"""
    CRITICAL = "critical"  # P0 - Immediate action required
    HIGH = "high"          # P1 - Next sprint
    MEDIUM = "medium"      # P2 - Backlog
    LOW = "low"            # P3 - Nice to have


class ImpactArea(Enum):
    """Areas of business impact"""
    REVENUE = "revenue"
    SECURITY = "security"
    PERFORMANCE = "performance"
    USER_EXPERIENCE = "user_experience"
    TECHNICAL_DEBT = "technical_debt"
    COMPLIANCE = "compliance"


@dataclass
class PriorityScore:
    """Priority scoring result"""
    ticket_id: str
    priority: PriorityLevel
    score: float  # 0-100
    impact_score: float
    complexity_score: float
    urgency_score: float
    sentiment_score: float
    reasoning: str
    impact_areas: List[ImpactArea]
    estimated_effort: str  # e.g., "2-4 hours", "1-2 days"
    dependencies: List[str]
    recommended_assignee: Optional[str] = None


@dataclass
class TicketAnalysis:
    """Detailed ticket analysis"""
    ticket_id: str
    title: str
    description: str
    labels: List[str]
    created_at: datetime
    updated_at: datetime
    comments_count: int
    reporter: str
    current_priority: Optional[str] = None


class TicketPrioritizer:
    """
    AI-powered ticket prioritization agent
    
    Uses multiple scoring algorithms and LLM analysis to determine
    optimal ticket priorities based on business value and technical factors.
    """
    
    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        model: str = "llama3"
    ):
        self.ollama = ollama_client or OllamaClient()
        self.model = model
        
        # Scoring weights
        self.weights = {
            "impact": 0.35,
            "complexity": 0.20,
            "urgency": 0.25,
            "sentiment": 0.20
        }
        
        # Priority thresholds
        self.thresholds = {
            PriorityLevel.CRITICAL: 85,
            PriorityLevel.HIGH: 70,
            PriorityLevel.MEDIUM: 50,
            PriorityLevel.LOW: 0
        }
    
    async def prioritize_ticket(
        self,
        ticket: TicketAnalysis
    ) -> PriorityScore:
        """
        Analyze and prioritize a single ticket
        
        Args:
            ticket: Ticket to analyze
            
        Returns:
            Priority score with detailed reasoning
        """
        logger.info(f"Prioritizing ticket: {ticket.ticket_id}")
        
        # Calculate individual scores
        impact_score = await self._calculate_impact_score(ticket)
        complexity_score = await self._calculate_complexity_score(ticket)
        urgency_score = await self._calculate_urgency_score(ticket)
        sentiment_score = await self._calculate_sentiment_score(ticket)
        
        # Calculate weighted total score
        total_score = (
            impact_score * self.weights["impact"] +
            complexity_score * self.weights["complexity"] +
            urgency_score * self.weights["urgency"] +
            sentiment_score * self.weights["sentiment"]
        )
        
        # Determine priority level
        priority = self._score_to_priority(total_score)
        
        # Identify impact areas
        impact_areas = await self._identify_impact_areas(ticket)
        
        # Estimate effort
        estimated_effort = await self._estimate_effort(ticket, complexity_score)
        
        # Find dependencies
        dependencies = await self._find_dependencies(ticket)
        
        # Generate reasoning
        reasoning = await self._generate_reasoning(
            ticket, total_score, impact_score, complexity_score,
            urgency_score, sentiment_score, impact_areas
        )
        
        # Recommend assignee
        recommended_assignee = await self._recommend_assignee(
            ticket, complexity_score, impact_areas
        )
        
        return PriorityScore(
            ticket_id=ticket.ticket_id,
            priority=priority,
            score=total_score,
            impact_score=impact_score,
            complexity_score=complexity_score,
            urgency_score=urgency_score,
            sentiment_score=sentiment_score,
            reasoning=reasoning,
            impact_areas=impact_areas,
            estimated_effort=estimated_effort,
            dependencies=dependencies,
            recommended_assignee=recommended_assignee
        )
    
    async def prioritize_batch(
        self,
        tickets: List[TicketAnalysis]
    ) -> List[PriorityScore]:
        """
        Prioritize multiple tickets in batch
        
        Args:
            tickets: List of tickets to prioritize
            
        Returns:
            List of priority scores, sorted by score descending
        """
        logger.info(f"Prioritizing {len(tickets)} tickets in batch")
        
        # Prioritize all tickets concurrently
        tasks = [self.prioritize_ticket(ticket) for ticket in tickets]
        scores = await asyncio.gather(*tasks)
        
        # Sort by score descending
        scores.sort(key=lambda x: x.score, reverse=True)
        
        return scores
    
    async def _calculate_impact_score(self, ticket: TicketAnalysis) -> float:
        """Calculate business impact score (0-100)"""
        
        # Keywords indicating high impact
        high_impact_keywords = [
            "revenue", "payment", "billing", "security", "breach",
            "data loss", "outage", "downtime", "critical", "urgent",
            "production", "customer", "compliance", "legal"
        ]
        
        medium_impact_keywords = [
            "performance", "slow", "bug", "error", "crash",
            "user experience", "ui", "ux", "feature"
        ]
        
        text = f"{ticket.title} {ticket.description}".lower()
        
        # Base score from keywords
        score = 30.0
        
        for keyword in high_impact_keywords:
            if keyword in text:
                score += 10.0
        
        for keyword in medium_impact_keywords:
            if keyword in text:
                score += 5.0
        
        # Label-based scoring
        for label in ticket.labels:
            label_lower = label.lower()
            if "critical" in label_lower or "p0" in label_lower:
                score += 20.0
            elif "high" in label_lower or "p1" in label_lower:
                score += 15.0
            elif "security" in label_lower:
                score += 15.0
            elif "bug" in label_lower:
                score += 10.0
        
        # Use LLM for deeper analysis
        prompt = f"""Analyze the business impact of this ticket on a scale of 0-100:

Title: {ticket.title}
Description: {ticket.description[:500]}
Labels: {', '.join(ticket.labels)}

Consider:
- Revenue impact
- Security implications
- User experience
- Compliance requirements
- Technical debt

Respond with ONLY a number between 0-100."""
        
        try:
            response = await self.ollama.generate(
                prompt=prompt,
                temperature=0.3
            )
            
            # Extract number from response
            llm_score = self._extract_number(response)
            if llm_score is not None:
                # Blend keyword score with LLM score (60/40 weight)
                score = score * 0.4 + llm_score * 0.6
        except Exception as e:
            logger.warning(f"LLM impact analysis failed: {e}")
        
        return min(100.0, score)
    
    async def _calculate_complexity_score(self, ticket: TicketAnalysis) -> float:
        """Calculate technical complexity score (0-100)"""
        
        complexity_keywords = {
            "high": ["architecture", "refactor", "migration", "redesign", "rewrite"],
            "medium": ["integration", "api", "database", "algorithm", "optimization"],
            "low": ["typo", "text", "copy", "color", "spacing", "alignment"]
        }
        
        text = f"{ticket.title} {ticket.description}".lower()
        
        score = 50.0  # Default medium complexity
        
        # Keyword-based scoring
        for keyword in complexity_keywords["high"]:
            if keyword in text:
                score += 10.0
        
        for keyword in complexity_keywords["medium"]:
            if keyword in text:
                score += 5.0
        
        for keyword in complexity_keywords["low"]:
            if keyword in text:
                score -= 10.0
        
        # Description length as complexity indicator
        desc_length = len(ticket.description)
        if desc_length > 1000:
            score += 10.0
        elif desc_length < 100:
            score -= 10.0
        
        return max(0.0, min(100.0, score))
    
    async def _calculate_urgency_score(self, ticket: TicketAnalysis) -> float:
        """Calculate urgency score (0-100)"""
        
        urgency_keywords = [
            "asap", "urgent", "immediately", "critical", "blocker",
            "blocking", "emergency", "now", "today"
        ]
        
        text = f"{ticket.title} {ticket.description}".lower()
        
        score = 30.0
        
        # Keyword-based scoring
        for keyword in urgency_keywords:
            if keyword in text:
                score += 15.0
        
        # Time-based urgency (older tickets may be more urgent)
        age_days = (datetime.utcnow() - ticket.created_at).days
        if age_days > 30:
            score += 20.0
        elif age_days > 14:
            score += 10.0
        elif age_days > 7:
            score += 5.0
        
        # Recent activity indicates urgency
        days_since_update = (datetime.utcnow() - ticket.updated_at).days
        if days_since_update < 1:
            score += 10.0
        
        # Comment count indicates urgency
        if ticket.comments_count > 10:
            score += 15.0
        elif ticket.comments_count > 5:
            score += 10.0
        
        return min(100.0, score)
    
    async def _calculate_sentiment_score(self, ticket: TicketAnalysis) -> float:
        """Calculate sentiment score from reporter/comments (0-100)"""
        
        # Negative sentiment keywords
        negative_keywords = [
            "frustrated", "angry", "disappointed", "terrible",
            "awful", "horrible", "unacceptable", "broken"
        ]
        
        # Positive sentiment keywords
        positive_keywords = [
            "nice to have", "enhancement", "improvement",
            "suggestion", "idea", "feature request"
        ]
        
        text = f"{ticket.title} {ticket.description}".lower()
        
        score = 50.0  # Neutral baseline
        
        # Negative sentiment increases priority
        for keyword in negative_keywords:
            if keyword in text:
                score += 10.0
        
        # Positive sentiment decreases priority
        for keyword in positive_keywords:
            if keyword in text:
                score -= 10.0
        
        return max(0.0, min(100.0, score))
    
    async def _identify_impact_areas(
        self,
        ticket: TicketAnalysis
    ) -> List[ImpactArea]:
        """Identify which business areas are impacted"""
        
        text = f"{ticket.title} {ticket.description}".lower()
        areas = []
        
        # Revenue impact
        if any(k in text for k in ["revenue", "payment", "billing", "subscription"]):
            areas.append(ImpactArea.REVENUE)
        
        # Security impact
        if any(k in text for k in ["security", "vulnerability", "breach", "exploit"]):
            areas.append(ImpactArea.SECURITY)
        
        # Performance impact
        if any(k in text for k in ["performance", "slow", "latency", "timeout"]):
            areas.append(ImpactArea.PERFORMANCE)
        
        # User experience impact
        if any(k in text for k in ["ux", "ui", "user experience", "usability"]):
            areas.append(ImpactArea.USER_EXPERIENCE)
        
        # Technical debt
        if any(k in text for k in ["refactor", "technical debt", "legacy", "deprecated"]):
            areas.append(ImpactArea.TECHNICAL_DEBT)
        
        # Compliance impact
        if any(k in text for k in ["compliance", "gdpr", "hipaa", "legal", "regulation"]):
            areas.append(ImpactArea.COMPLIANCE)
        
        return areas if areas else [ImpactArea.USER_EXPERIENCE]
    
    async def _estimate_effort(
        self,
        ticket: TicketAnalysis,
        complexity_score: float
    ) -> str:
        """Estimate effort required"""
        
        if complexity_score < 30:
            return "1-2 hours"
        elif complexity_score < 50:
            return "2-4 hours"
        elif complexity_score < 70:
            return "1-2 days"
        elif complexity_score < 85:
            return "3-5 days"
        else:
            return "1-2 weeks"
    
    async def _find_dependencies(self, ticket: TicketAnalysis) -> List[str]:
        """Find ticket dependencies from description"""
        
        dependencies = []
        
        # Look for ticket references (e.g., #123, PROJ-456)
        patterns = [
            r'#(\d+)',
            r'([A-Z]+-\d+)',
            r'depends on #(\d+)',
            r'blocked by #(\d+)'
        ]
        
        text = f"{ticket.title} {ticket.description}"
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            dependencies.extend(matches)
        
        return list(set(dependencies))
    
    async def _generate_reasoning(
        self,
        ticket: TicketAnalysis,
        total_score: float,
        impact_score: float,
        complexity_score: float,
        urgency_score: float,
        sentiment_score: float,
        impact_areas: List[ImpactArea]
    ) -> str:
        """Generate human-readable reasoning for priority"""
        
        prompt = f"""Generate a concise explanation (2-3 sentences) for why this ticket received a priority score of {total_score:.1f}/100:

Title: {ticket.title}
Impact Score: {impact_score:.1f}/100
Complexity Score: {complexity_score:.1f}/100
Urgency Score: {urgency_score:.1f}/100
Sentiment Score: {sentiment_score:.1f}/100
Impact Areas: {', '.join(a.value for a in impact_areas)}

Focus on the most important factors."""
        
        try:
            reasoning = await self.ollama.generate(
                prompt=prompt,
                temperature=0.5
            )
            return reasoning.strip()
        except Exception as e:
            logger.warning(f"Failed to generate reasoning: {e}")
            return f"Priority {total_score:.1f}/100 based on impact ({impact_score:.1f}), complexity ({complexity_score:.1f}), and urgency ({urgency_score:.1f})."
    
    async def _recommend_assignee(
        self,
        ticket: TicketAnalysis,
        complexity_score: float,
        impact_areas: List[ImpactArea]
    ) -> Optional[str]:
        """Recommend best assignee based on ticket characteristics"""
        
        # This would integrate with team member skills/availability
        # For now, return role-based recommendations
        
        if ImpactArea.SECURITY in impact_areas:
            return "security-team"
        elif ImpactArea.REVENUE in impact_areas:
            return "backend-team"
        elif ImpactArea.USER_EXPERIENCE in impact_areas:
            return "frontend-team"
        elif complexity_score > 80:
            return "senior-engineer"
        else:
            return None
    
    def _score_to_priority(self, score: float) -> PriorityLevel:
        """Convert numeric score to priority level"""
        
        if score >= self.thresholds[PriorityLevel.CRITICAL]:
            return PriorityLevel.CRITICAL
        elif score >= self.thresholds[PriorityLevel.HIGH]:
            return PriorityLevel.HIGH
        elif score >= self.thresholds[PriorityLevel.MEDIUM]:
            return PriorityLevel.MEDIUM
        else:
            return PriorityLevel.LOW
    
    def _extract_number(self, text: str) -> Optional[float]:
        """Extract a number from text"""
        
        # Try to find a number in the text
        match = re.search(r'\b(\d+(?:\.\d+)?)\b', text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None
    
    async def get_priority_distribution(
        self,
        scores: List[PriorityScore]
    ) -> Dict[str, int]:
        """Get distribution of priorities"""
        
        distribution = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for score in scores:
            distribution[score.priority.value] += 1
        
        return distribution
    
    async def get_top_priorities(
        self,
        scores: List[PriorityScore],
        limit: int = 10
    ) -> List[PriorityScore]:
        """Get top N priority tickets"""
        
        return sorted(scores, key=lambda x: x.score, reverse=True)[:limit]

# Made with Bob
