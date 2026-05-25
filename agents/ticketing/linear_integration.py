"""
Linear Integration Agent - Linear API Integration

Integrates with Linear for ticket management:
- Issue creation and updates
- Project synchronization
- Label management
- Milestone tracking
- Team coordination
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import httpx

from backend.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class IssueStatus(str, Enum):
    """Linear issue status"""
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELED = "canceled"


class IssuePriority(str, Enum):
    """Linear issue priority"""
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NO_PRIORITY = "no_priority"


@dataclass
class LinearIssue:
    """Linear issue"""
    id: str
    title: str
    description: Optional[str]
    status: IssueStatus
    priority: IssuePriority
    assignee_id: Optional[str]
    team_id: str
    project_id: Optional[str]
    labels: List[str]
    created_at: datetime
    updated_at: datetime
    url: str


class LinearIntegration:
    """
    Autonomous Linear integration agent.
    
    Capabilities:
    - Issue creation and management
    - Project synchronization
    - Label management
    - Milestone tracking
    - Team coordination
    - AI-powered issue descriptions
    - Automated issue updates
    """
    
    def __init__(
        self,
        api_key: str,
        ollama_client: Optional[OllamaClient] = None,
    ):
        self.api_key = api_key
        self.ollama = ollama_client or OllamaClient()
        self.base_url = "https://api.linear.app/graphql"
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        
        logger.info("Linear Integration initialized")
    
    async def create_issue(
        self,
        team_id: str,
        title: str,
        description: Optional[str] = None,
        priority: IssuePriority = IssuePriority.MEDIUM,
        assignee_id: Optional[str] = None,
        project_id: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> LinearIssue:
        """Create a new Linear issue"""
        logger.info(f"Creating Linear issue: {title}")
        
        # Generate description if not provided
        if not description:
            description = await self._generate_description(title)
        
        # GraphQL mutation
        mutation = """
        mutation IssueCreate($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    title
                    description
                    state {
                        name
                    }
                    priority
                    assignee {
                        id
                    }
                    team {
                        id
                    }
                    project {
                        id
                    }
                    labels {
                        nodes {
                            name
                        }
                    }
                    createdAt
                    updatedAt
                    url
                }
            }
        }
        """
        
        variables = {
            "input": {
                "teamId": team_id,
                "title": title,
                "description": description,
                "priority": self._priority_to_number(priority),
            }
        }
        
        if assignee_id:
            variables["input"]["assigneeId"] = assignee_id
        if project_id:
            variables["input"]["projectId"] = project_id
        if labels:
            variables["input"]["labelIds"] = labels
        
        response = await self._execute_query(mutation, variables)
        
        if response.get("data", {}).get("issueCreate", {}).get("success"):
            issue_data = response["data"]["issueCreate"]["issue"]
            return self._parse_issue(issue_data)
        else:
            raise Exception(f"Failed to create issue: {response}")
    
    async def update_issue(
        self,
        issue_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[IssueStatus] = None,
        priority: Optional[IssuePriority] = None,
        assignee_id: Optional[str] = None,
    ) -> LinearIssue:
        """Update an existing Linear issue"""
        logger.info(f"Updating Linear issue: {issue_id}")
        
        mutation = """
        mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
                issue {
                    id
                    title
                    description
                    state {
                        name
                    }
                    priority
                    assignee {
                        id
                    }
                    team {
                        id
                    }
                    project {
                        id
                    }
                    labels {
                        nodes {
                            name
                        }
                    }
                    createdAt
                    updatedAt
                    url
                }
            }
        }
        """
        
        variables = {
            "id": issue_id,
            "input": {}
        }
        
        if title:
            variables["input"]["title"] = title
        if description:
            variables["input"]["description"] = description
        if status:
            variables["input"]["stateId"] = await self._get_state_id(status)
        if priority:
            variables["input"]["priority"] = self._priority_to_number(priority)
        if assignee_id:
            variables["input"]["assigneeId"] = assignee_id
        
        response = await self._execute_query(mutation, variables)
        
        if response.get("data", {}).get("issueUpdate", {}).get("success"):
            issue_data = response["data"]["issueUpdate"]["issue"]
            return self._parse_issue(issue_data)
        else:
            raise Exception(f"Failed to update issue: {response}")
    
    async def get_issue(self, issue_id: str) -> LinearIssue:
        """Get a Linear issue by ID"""
        query = """
        query Issue($id: String!) {
            issue(id: $id) {
                id
                title
                description
                state {
                    name
                }
                priority
                assignee {
                    id
                }
                team {
                    id
                }
                project {
                    id
                }
                labels {
                    nodes {
                        name
                    }
                }
                createdAt
                updatedAt
                url
            }
        }
        """
        
        response = await self._execute_query(query, {"id": issue_id})
        issue_data = response.get("data", {}).get("issue")
        
        if issue_data:
            return self._parse_issue(issue_data)
        else:
            raise Exception(f"Issue not found: {issue_id}")
    
    async def list_issues(
        self,
        team_id: str,
        status: Optional[IssueStatus] = None,
        assignee_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[LinearIssue]:
        """List Linear issues with filters"""
        query = """
        query Issues($filter: IssueFilter, $first: Int) {
            issues(filter: $filter, first: $first) {
                nodes {
                    id
                    title
                    description
                    state {
                        name
                    }
                    priority
                    assignee {
                        id
                    }
                    team {
                        id
                    }
                    project {
                        id
                    }
                    labels {
                        nodes {
                            name
                        }
                    }
                    createdAt
                    updatedAt
                    url
                }
            }
        }
        """
        
        filter_obj = {"team": {"id": {"eq": team_id}}}
        
        if status:
            filter_obj["state"] = {"name": {"eq": status.value}}
        if assignee_id:
            filter_obj["assignee"] = {"id": {"eq": assignee_id}}
        
        response = await self._execute_query(
            query,
            {"filter": filter_obj, "first": limit}
        )
        
        issues_data = response.get("data", {}).get("issues", {}).get("nodes", [])
        return [self._parse_issue(issue) for issue in issues_data]
    
    async def add_comment(
        self,
        issue_id: str,
        body: str,
    ) -> Dict[str, Any]:
        """Add a comment to an issue"""
        mutation = """
        mutation CommentCreate($input: CommentCreateInput!) {
            commentCreate(input: $input) {
                success
                comment {
                    id
                    body
                    createdAt
                }
            }
        }
        """
        
        variables = {
            "input": {
                "issueId": issue_id,
                "body": body,
            }
        }
        
        response = await self._execute_query(mutation, variables)
        return response.get("data", {}).get("commentCreate", {})
    
    async def _execute_query(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute GraphQL query"""
        try:
            response = await self.client.post(
                self.base_url,
                json={"query": query, "variables": variables or {}}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Linear API error: {e}")
            raise
    
    def _parse_issue(self, data: Dict[str, Any]) -> LinearIssue:
        """Parse Linear issue from API response"""
        return LinearIssue(
            id=data["id"],
            title=data["title"],
            description=data.get("description"),
            status=IssueStatus(data["state"]["name"].lower().replace(" ", "_")),
            priority=self._number_to_priority(data.get("priority", 0)),
            assignee_id=data.get("assignee", {}).get("id"),
            team_id=data["team"]["id"],
            project_id=data.get("project", {}).get("id"),
            labels=[label["name"] for label in data.get("labels", {}).get("nodes", [])],
            created_at=datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updatedAt"].replace("Z", "+00:00")),
            url=data["url"],
        )
    
    def _priority_to_number(self, priority: IssuePriority) -> int:
        """Convert priority enum to Linear priority number"""
        mapping = {
            IssuePriority.URGENT: 1,
            IssuePriority.HIGH: 2,
            IssuePriority.MEDIUM: 3,
            IssuePriority.LOW: 4,
            IssuePriority.NO_PRIORITY: 0,
        }
        return mapping.get(priority, 0)
    
    def _number_to_priority(self, number: int) -> IssuePriority:
        """Convert Linear priority number to priority enum"""
        mapping = {
            1: IssuePriority.URGENT,
            2: IssuePriority.HIGH,
            3: IssuePriority.MEDIUM,
            4: IssuePriority.LOW,
            0: IssuePriority.NO_PRIORITY,
        }
        return mapping.get(number, IssuePriority.NO_PRIORITY)
    
    async def _get_state_id(self, status: IssueStatus) -> str:
        """Get Linear state ID for status"""
        # TODO: Implement state ID lookup
        return "state-id"
    
    async def _generate_description(self, title: str) -> str:
        """Generate AI-powered issue description"""
        prompt = f"""
        Generate a clear, concise issue description for:
        
        Title: {title}
        
        Include:
        1. Brief description of the issue
        2. Expected behavior
        3. Steps to reproduce (if applicable)
        4. Acceptance criteria
        
        Keep it professional and actionable.
        """
        
        description = await self.ollama.generate(
            prompt,
            system="You are a technical project manager writing issue descriptions."
        )
        
        return description.strip()
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        await self.client.aclose()
        await self.ollama.close()

# Made with Bob
