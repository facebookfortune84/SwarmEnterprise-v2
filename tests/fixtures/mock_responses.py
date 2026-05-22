"""
Mock LLM and API responses for testing
"""
from typing import Dict, Any, List


# Mock LLM responses for agent testing
MOCK_LLM_RESPONSES = {
    "board_convene": {
        "role": "assistant",
        "content": """Based on the requirements, I recommend the following approach:
        
1. Create a FastAPI backend with PostgreSQL
2. Build a React frontend with Tailwind CSS
3. Implement JWT authentication
4. Set up Docker deployment

I'll create tickets for the development team."""
    },
    
    "ticket_generation": {
        "role": "assistant",
        "content": """[
    {
        "ticket_id": "TKT-001",
        "department": "Engineering",
        "priority": "high",
        "title": "Implement authentication system",
        "instruction": "Create JWT-based authentication with user registration and login"
    },
    {
        "ticket_id": "TKT-002",
        "department": "Engineering",
        "priority": "medium",
        "title": "Set up database models",
        "instruction": "Create SQLAlchemy models for users, companies, and deployments"
    }
]"""
    },
    
    "code_generation": {
        "role": "assistant",
        "content": """```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    email: str
    password: str

@app.post("/api/auth/register")
async def register(user: User):
    # Implementation here
    return {"message": "User registered successfully"}
```"""
    },
    
    "code_review": {
        "role": "assistant",
        "content": """Code review feedback:

✅ Good practices:
- Proper type hints
- Clear function names
- Good error handling

⚠️ Suggestions:
- Add input validation
- Include docstrings
- Add unit tests

Overall: APPROVED with minor suggestions"""
    }
}


# Mock Stripe API responses
MOCK_STRIPE_RESPONSES = {
    "create_customer": {
        "id": "cus_test123",
        "email": "test@example.com",
        "created": 1234567890
    },
    
    "create_subscription": {
        "id": "sub_test123",
        "customer": "cus_test123",
        "status": "active",
        "current_period_start": 1234567890,
        "current_period_end": 1237159890
    },
    
    "create_checkout_session": {
        "id": "cs_test123",
        "url": "https://checkout.stripe.com/test123",
        "payment_status": "unpaid"
    }
}


# Mock GitHub API responses
MOCK_GITHUB_RESPONSES = {
    "create_issue": {
        "id": 1,
        "number": 123,
        "title": "Test Issue",
        "state": "open",
        "html_url": "https://github.com/test/repo/issues/123"
    },
    
    "create_pr": {
        "id": 1,
        "number": 456,
        "title": "Test PR",
        "state": "open",
        "html_url": "https://github.com/test/repo/pull/456"
    }
}


# Mock health check responses
MOCK_HEALTH_RESPONSES = {
    "healthy": {
        "status": "healthy",
        "checks": {
            "database": "ok",
            "redis": "ok",
            "storage": "ok"
        }
    },
    
    "unhealthy": {
        "status": "unhealthy",
        "checks": {
            "database": "ok",
            "redis": "failed",
            "storage": "ok"
        }
    }
}


def get_mock_llm_response(prompt_type: str) -> Dict[str, Any]:
    """Get a mock LLM response for testing"""
    return MOCK_LLM_RESPONSES.get(prompt_type, {
        "role": "assistant",
        "content": "Mock response"
    })


def get_mock_api_response(service: str, endpoint: str) -> Dict[str, Any]:
    """Get a mock API response for testing"""
    responses = {
        "stripe": MOCK_STRIPE_RESPONSES,
        "github": MOCK_GITHUB_RESPONSES,
        "health": MOCK_HEALTH_RESPONSES
    }
    return responses.get(service, {}).get(endpoint, {})

# Made with Bob
