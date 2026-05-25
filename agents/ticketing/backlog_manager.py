"""
Backlog Manager Agent

Automatically organizes and maintains the product backlog:
- Groups related tickets
- Identifies epics and themes
- Suggests sprint planning
- Detects duplicate tickets
- Maintains backlog health
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional
from collections import defaultdict

from backend.llm.ollama_client import OllamaClient
from agents.ticketing.ticket_prioritizer import (
    PriorityScore,
    PriorityLevel,
    TicketAnalysis
)


logger = logging.getLogger(__name__)


class BacklogHealth(Enum):
    """Backlog health status"""
    EXCELLENT = "excellent"  # Well-organized, balanced
    GOOD = "good"            # Minor issues
    FAIR = "fair"            # Needs attention
    POOR = "poor"            # Requires immediate cleanup


@dataclass
class Epic:
    """Epic grouping of related tickets"""
    id: str
    title: str
    description: str
    ticket_ids: List[str]
    priority: PriorityLevel
    estimated_effort: str
    completion_percentage: float
    theme: str


@dataclass
class SprintSuggestion:
    """Sprint planning suggestion"""
    sprint_number: int
    start_date: datetime
    end_date: datetime
    ticket_ids: List[str]
    total_story_points: int
    focus_areas: List[str]
    risks: List[str]
    dependencies: List[str]


@dataclass
class DuplicateGroup:
    """Group of duplicate tickets"""
    primary_ticket_id: str
    duplicate_ticket_ids: List[str]
    similarity_score: float
    reason: str


@dataclass
class BacklogReport:
    """Comprehensive backlog health report"""
    health_status: BacklogHealth
    total_tickets: int
    priority_distribution: Dict[str, int]
    epics: List[Epic]
    sprint_suggestions: List[SprintSuggestion]
    duplicates: List[DuplicateGroup]
    stale_tickets: List[str]
    blocked_tickets: List[str]
    recommendations: List[str]
    generated_at: datetime


class BacklogManager:
    """
    AI-powered backlog management agent
    
    Maintains a healthy, organized backlog by:
    - Automatically grouping related tickets into epics
    - Detecting and flagging duplicate tickets
    - Suggesting sprint planning
    - Identifying stale or blocked tickets
    - Providing actionable recommendations
    """
    
    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        model: str = "llama3"
    ):
        self.ollama = ollama_client or OllamaClient()
        self.model = model
        
        # Configuration
        self.stale_threshold_days = 90
        self.duplicate_similarity_threshold = 0.75
        self.sprint_capacity_points = 40  # Default team capacity
        self.sprint_duration_days = 14
    
    async def analyze_backlog(
        self,
        tickets: List[TicketAnalysis],
        priority_scores: List[PriorityScore]
    ) -> BacklogReport:
        """
        Perform comprehensive backlog analysis
        
        Args:
            tickets: All tickets in backlog
            priority_scores: Priority scores for tickets
            
        Returns:
            Detailed backlog report with recommendations
        """
        logger.info(f"Analyzing backlog with {len(tickets)} tickets")
        
        # Create ticket lookup
        {t.ticket_id: t for t in tickets}
        {s.ticket_id: s for s in priority_scores}
        
        # Run all analyses concurrently
        epics_task = self.identify_epics(tickets, priority_scores)
        duplicates_task = self.find_duplicates(tickets)
        stale_task = self.find_stale_tickets(tickets)
        blocked_task = self.find_blocked_tickets(tickets, priority_scores)
        sprints_task = self.suggest_sprints(tickets, priority_scores)
        
        epics, duplicates, stale, blocked, sprints = await asyncio.gather(
            epics_task,
            duplicates_task,
            stale_task,
            blocked_task,
            sprints_task
        )
        
        # Calculate priority distribution
        priority_dist = self._calculate_priority_distribution(priority_scores)
        
        # Determine health status
        health = self._assess_health(
            len(tickets),
            priority_dist,
            len(duplicates),
            len(stale),
            len(blocked)
        )
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(
            health,
            len(tickets),
            priority_dist,
            len(duplicates),
            len(stale),
            len(blocked)
        )
        
        return BacklogReport(
            health_status=health,
            total_tickets=len(tickets),
            priority_distribution=priority_dist,
            epics=epics,
            sprint_suggestions=sprints,
            duplicates=duplicates,
            stale_tickets=stale,
            blocked_tickets=blocked,
            recommendations=recommendations,
            generated_at=datetime.utcnow()
        )
    
    async def identify_epics(
        self,
        tickets: List[TicketAnalysis],
        priority_scores: List[PriorityScore]
    ) -> List[Epic]:
        """
        Identify and group tickets into epics
        
        Args:
            tickets: All tickets
            priority_scores: Priority scores
            
        Returns:
            List of identified epics
        """
        logger.info("Identifying epics from tickets")
        
        # Group tickets by theme/feature area
        theme_groups = await self._group_by_theme(tickets)
        
        epics = []
        score_map = {s.ticket_id: s for s in priority_scores}
        
        for theme, ticket_ids in theme_groups.items():
            if len(ticket_ids) < 3:  # Skip small groups
                continue
            
            theme_tickets = [t for t in tickets if t.ticket_id in ticket_ids]
            
            # Calculate epic priority (highest priority ticket)
            epic_priority = PriorityLevel.LOW
            for tid in ticket_ids:
                if tid in score_map:
                    score = score_map[tid]
                    if score.priority.value == "critical":
                        epic_priority = PriorityLevel.CRITICAL
                        break
                    elif score.priority.value == "high" and epic_priority != PriorityLevel.CRITICAL:
                        epic_priority = PriorityLevel.HIGH
                    elif score.priority.value == "medium" and epic_priority == PriorityLevel.LOW:
                        epic_priority = PriorityLevel.MEDIUM
            
            # Generate epic title and description
            epic_title = await self._generate_epic_title(theme, theme_tickets)
            epic_desc = await self._generate_epic_description(theme, theme_tickets)
            
            # Calculate completion percentage (if any tickets are done)
            completion = 0.0  # Would integrate with actual ticket status
            
            # Estimate total effort
            total_effort = self._estimate_epic_effort(ticket_ids, score_map)
            
            epic = Epic(
                id=f"EPIC-{theme.upper().replace(' ', '-')}",
                title=epic_title,
                description=epic_desc,
                ticket_ids=ticket_ids,
                priority=epic_priority,
                estimated_effort=total_effort,
                completion_percentage=completion,
                theme=theme
            )
            
            epics.append(epic)
        
        # Sort by priority
        priority_order = {
            PriorityLevel.CRITICAL: 0,
            PriorityLevel.HIGH: 1,
            PriorityLevel.MEDIUM: 2,
            PriorityLevel.LOW: 3
        }
        epics.sort(key=lambda e: priority_order[e.priority])
        
        return epics
    
    async def find_duplicates(
        self,
        tickets: List[TicketAnalysis]
    ) -> List[DuplicateGroup]:
        """
        Find duplicate or very similar tickets
        
        Args:
            tickets: All tickets
            
        Returns:
            List of duplicate groups
        """
        logger.info("Searching for duplicate tickets")
        
        duplicates = []
        processed = set()
        
        for i, ticket1 in enumerate(tickets):
            if ticket1.ticket_id in processed:
                continue
            
            similar_tickets = []
            
            for ticket2 in tickets[i+1:]:
                if ticket2.ticket_id in processed:
                    continue
                
                # Calculate similarity
                similarity = await self._calculate_similarity(ticket1, ticket2)
                
                if similarity >= self.duplicate_similarity_threshold:
                    similar_tickets.append((ticket2.ticket_id, similarity))
            
            if similar_tickets:
                # Generate reason for duplication
                reason = await self._explain_duplication(
                    ticket1,
                    [t for t in tickets if t.ticket_id in [st[0] for st in similar_tickets]]
                )
                
                duplicate_ids = [st[0] for st in similar_tickets]
                
                duplicates.append(DuplicateGroup(
                    primary_ticket_id=ticket1.ticket_id,
                    duplicate_ticket_ids=duplicate_ids,
                    similarity_score=max(st[1] for st in similar_tickets),
                    reason=reason
                ))
                
                processed.add(ticket1.ticket_id)
                processed.update(duplicate_ids)
        
        return duplicates
    
    async def find_stale_tickets(
        self,
        tickets: List[TicketAnalysis]
    ) -> List[str]:
        """
        Find tickets that haven't been updated in a long time
        
        Args:
            tickets: All tickets
            
        Returns:
            List of stale ticket IDs
        """
        threshold = datetime.utcnow() - timedelta(days=self.stale_threshold_days)
        
        stale = [
            t.ticket_id
            for t in tickets
            if t.updated_at < threshold
        ]
        
        logger.info(f"Found {len(stale)} stale tickets")
        return stale
    
    async def find_blocked_tickets(
        self,
        tickets: List[TicketAnalysis],
        priority_scores: List[PriorityScore]
    ) -> List[str]:
        """
        Find tickets that are blocked by dependencies
        
        Args:
            tickets: All tickets
            priority_scores: Priority scores with dependencies
            
        Returns:
            List of blocked ticket IDs
        """
        score_map = {s.ticket_id: s for s in priority_scores}
        
        blocked = []
        
        for ticket in tickets:
            if ticket.ticket_id in score_map:
                score = score_map[ticket.ticket_id]
                if score.dependencies:
                    # Check if any dependencies are unresolved
                    # In real implementation, would check ticket status
                    blocked.append(ticket.ticket_id)
        
        logger.info(f"Found {len(blocked)} blocked tickets")
        return blocked
    
    async def suggest_sprints(
        self,
        tickets: List[TicketAnalysis],
        priority_scores: List[PriorityScore],
        num_sprints: int = 3
    ) -> List[SprintSuggestion]:
        """
        Suggest sprint planning based on priorities and capacity
        
        Args:
            tickets: All tickets
            priority_scores: Priority scores
            num_sprints: Number of sprints to plan
            
        Returns:
            List of sprint suggestions
        """
        logger.info(f"Generating {num_sprints} sprint suggestions")
        
        # Sort tickets by priority score
        sorted_scores = sorted(priority_scores, key=lambda x: x.score, reverse=True)
        
        sprints = []
        start_date = datetime.utcnow()
        
        for sprint_num in range(1, num_sprints + 1):
            # Calculate sprint dates
            sprint_start = start_date + timedelta(days=(sprint_num - 1) * self.sprint_duration_days)
            sprint_end = sprint_start + timedelta(days=self.sprint_duration_days)
            
            # Select tickets for sprint (up to capacity)
            sprint_tickets = []
            total_points = 0
            
            for score in sorted_scores:
                if score.ticket_id in [t for sprint in sprints for t in sprint.ticket_ids]:
                    continue  # Already assigned
                
                # Estimate story points from effort
                points = self._effort_to_points(score.estimated_effort)
                
                if total_points + points <= self.sprint_capacity_points:
                    sprint_tickets.append(score.ticket_id)
                    total_points += points
            
            if not sprint_tickets:
                break
            
            # Identify focus areas
            focus_areas = self._identify_focus_areas(
                [s for s in sorted_scores if s.ticket_id in sprint_tickets]
            )
            
            # Identify risks
            risks = self._identify_sprint_risks(
                [s for s in sorted_scores if s.ticket_id in sprint_tickets]
            )
            
            # Collect dependencies
            dependencies = []
            for tid in sprint_tickets:
                score = next((s for s in sorted_scores if s.ticket_id == tid), None)
                if score and score.dependencies:
                    dependencies.extend(score.dependencies)
            
            sprints.append(SprintSuggestion(
                sprint_number=sprint_num,
                start_date=sprint_start,
                end_date=sprint_end,
                ticket_ids=sprint_tickets,
                total_story_points=total_points,
                focus_areas=focus_areas,
                risks=risks,
                dependencies=list(set(dependencies))
            ))
        
        return sprints
    
    async def _group_by_theme(
        self,
        tickets: List[TicketAnalysis]
    ) -> Dict[str, List[str]]:
        """Group tickets by theme/feature area"""
        
        # Use labels and keywords to group
        theme_groups = defaultdict(list)
        
        for ticket in tickets:
            # Extract theme from labels
            theme = "general"
            
            for label in ticket.labels:
                label_lower = label.lower()
                if any(k in label_lower for k in ["feature", "epic", "theme"]):
                    theme = label
                    break
            
            # If no theme label, use keywords from title
            if theme == "general":
                title_lower = ticket.title.lower()
                if "auth" in title_lower or "login" in title_lower:
                    theme = "authentication"
                elif "payment" in title_lower or "billing" in title_lower:
                    theme = "payments"
                elif "ui" in title_lower or "frontend" in title_lower:
                    theme = "frontend"
                elif "api" in title_lower or "backend" in title_lower:
                    theme = "backend"
                elif "deploy" in title_lower or "infra" in title_lower:
                    theme = "infrastructure"
            
            theme_groups[theme].append(ticket.ticket_id)
        
        return dict(theme_groups)
    
    async def _generate_epic_title(
        self,
        theme: str,
        tickets: List[TicketAnalysis]
    ) -> str:
        """Generate epic title from theme and tickets"""
        
        # Simple title generation
        return f"{theme.title()} Epic"
    
    async def _generate_epic_description(
        self,
        theme: str,
        tickets: List[TicketAnalysis]
    ) -> str:
        """Generate epic description"""
        
        ticket_titles = [t.title for t in tickets[:5]]  # First 5
        
        prompt = f"""Generate a concise epic description (2-3 sentences) for a group of related tickets:

Theme: {theme}
Sample Tickets:
{chr(10).join(f'- {title}' for title in ticket_titles)}

Focus on the overall goal and value."""
        
        try:
            description = await self.ollama.generate(
                prompt=prompt,
                temperature=0.5
            )
            return description.strip()
        except Exception as e:
            logger.warning(f"Failed to generate epic description: {e}")
            return f"Epic for {theme} related features and improvements."
    
    def _estimate_epic_effort(
        self,
        ticket_ids: List[str],
        score_map: Dict[str, PriorityScore]
    ) -> str:
        """Estimate total effort for epic"""
        
        total_hours = 0
        
        for tid in ticket_ids:
            if tid in score_map:
                effort = score_map[tid].estimated_effort
                # Convert to hours
                if "hour" in effort:
                    hours = int(effort.split("-")[0])
                    total_hours += hours
                elif "day" in effort:
                    days = int(effort.split("-")[0])
                    total_hours += days * 8
                elif "week" in effort:
                    weeks = int(effort.split("-")[0])
                    total_hours += weeks * 40
        
        if total_hours < 40:
            return f"{total_hours} hours"
        elif total_hours < 160:
            return f"{total_hours // 8} days"
        else:
            return f"{total_hours // 40} weeks"
    
    async def _calculate_similarity(
        self,
        ticket1: TicketAnalysis,
        ticket2: TicketAnalysis
    ) -> float:
        """Calculate similarity between two tickets (0-1)"""
        
        # Simple keyword-based similarity
        words1 = set(ticket1.title.lower().split())
        words2 = set(ticket2.title.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    async def _explain_duplication(
        self,
        primary: TicketAnalysis,
        duplicates: List[TicketAnalysis]
    ) -> str:
        """Explain why tickets are duplicates"""
        
        return "Similar titles and descriptions suggest these tickets address the same issue."
    
    def _calculate_priority_distribution(
        self,
        priority_scores: List[PriorityScore]
    ) -> Dict[str, int]:
        """Calculate distribution of priorities"""
        
        dist = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for score in priority_scores:
            dist[score.priority.value] += 1
        
        return dist
    
    def _assess_health(
        self,
        total_tickets: int,
        priority_dist: Dict[str, int],
        num_duplicates: int,
        num_stale: int,
        num_blocked: int
    ) -> BacklogHealth:
        """Assess overall backlog health"""
        
        issues = 0
        
        # Too many tickets
        if total_tickets > 200:
            issues += 2
        elif total_tickets > 100:
            issues += 1
        
        # Unbalanced priorities
        if priority_dist.get("critical", 0) > total_tickets * 0.2:
            issues += 2
        
        # Duplicates
        if num_duplicates > 5:
            issues += 2
        elif num_duplicates > 0:
            issues += 1
        
        # Stale tickets
        stale_ratio = num_stale / max(total_tickets, 1)
        if stale_ratio > 0.3:
            issues += 2
        elif stale_ratio > 0.15:
            issues += 1
        
        # Blocked tickets
        blocked_ratio = num_blocked / max(total_tickets, 1)
        if blocked_ratio > 0.2:
            issues += 2
        elif blocked_ratio > 0.1:
            issues += 1
        
        # Determine health
        if issues == 0:
            return BacklogHealth.EXCELLENT
        elif issues <= 2:
            return BacklogHealth.GOOD
        elif issues <= 5:
            return BacklogHealth.FAIR
        else:
            return BacklogHealth.POOR
    
    async def _generate_recommendations(
        self,
        health: BacklogHealth,
        total_tickets: int,
        priority_dist: Dict[str, int],
        num_duplicates: int,
        num_stale: int,
        num_blocked: int
    ) -> List[str]:
        """Generate actionable recommendations"""
        
        recommendations = []
        
        if total_tickets > 100:
            recommendations.append(
                f"Backlog has {total_tickets} tickets. Consider archiving or closing completed/obsolete tickets."
            )
        
        if priority_dist.get("critical", 0) > 10:
            recommendations.append(
                f"{priority_dist['critical']} critical tickets. Review if all are truly critical."
            )
        
        if num_duplicates > 0:
            recommendations.append(
                f"Found {num_duplicates} duplicate groups. Merge or close duplicates to reduce noise."
            )
        
        if num_stale > 0:
            recommendations.append(
                f"{num_stale} tickets haven't been updated in {self.stale_threshold_days} days. Review and update or close."
            )
        
        if num_blocked > 0:
            recommendations.append(
                f"{num_blocked} tickets are blocked by dependencies. Prioritize unblocking work."
            )
        
        if health == BacklogHealth.EXCELLENT:
            recommendations.append("Backlog is well-maintained. Keep up the good work!")
        
        return recommendations
    
    def _effort_to_points(self, effort: str) -> int:
        """Convert effort estimate to story points"""
        
        if "hour" in effort:
            hours = int(effort.split("-")[0])
            return max(1, hours // 2)
        elif "day" in effort:
            days = int(effort.split("-")[0])
            return days * 4
        elif "week" in effort:
            weeks = int(effort.split("-")[0])
            return weeks * 20
        else:
            return 5  # Default
    
    def _identify_focus_areas(
        self,
        scores: List[PriorityScore]
    ) -> List[str]:
        """Identify focus areas for sprint"""
        
        areas = set()
        
        for score in scores:
            for area in score.impact_areas:
                areas.add(area.value)
        
        return list(areas)[:3]  # Top 3
    
    def _identify_sprint_risks(
        self,
        scores: List[PriorityScore]
    ) -> List[str]:
        """Identify risks for sprint"""
        
        risks = []
        
        # High complexity tickets
        high_complexity = [s for s in scores if s.complexity_score > 70]
        if high_complexity:
            risks.append(f"{len(high_complexity)} high-complexity tickets may require more time")
        
        # Tickets with dependencies
        with_deps = [s for s in scores if s.dependencies]
        if with_deps:
            risks.append(f"{len(with_deps)} tickets have external dependencies")
        
        return risks

# Made with Bob
