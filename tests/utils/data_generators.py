"""
Data generators for testing
"""
import random
import string
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


def random_string(length: int = 10, chars: str = string.ascii_lowercase) -> str:
    """Generate a random string"""
    return ''.join(random.choice(chars) for _ in range(length))


def random_email() -> str:
    """Generate a random email address"""
    username = random_string(8)
    domain = random_string(6)
    return f"{username}@{domain}.com"


def random_slug() -> str:
    """Generate a random slug"""
    return random_string(12, string.ascii_lowercase + string.digits + '-')


def random_subdomain() -> str:
    """Generate a random subdomain"""
    return random_string(8, string.ascii_lowercase + string.digits)


def random_datetime(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None
) -> datetime:
    """Generate a random datetime between start and end"""
    if start is None:
        start = datetime.utcnow() - timedelta(days=365)
    if end is None:
        end = datetime.utcnow()
    
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


def generate_users(count: int = 10) -> List[Dict[str, Any]]:
    """Generate multiple test users"""
    from tests.fixtures.users import create_test_user
    
    users = []
    for i in range(count):
        users.append(create_test_user(
            email=random_email(),
            full_name=f"Test User {i+1}",
            role=random.choice(["user", "user", "user", "admin"]),  # 75% users, 25% admins
            subscription_tier=random.choice(["free", "basic", "premium"])
        ))
    return users


def generate_companies(count: int = 10, user_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Generate multiple test companies"""
    from tests.fixtures.companies import create_test_company
    
    if user_ids is None:
        user_ids = [random_string(36) for _ in range(count)]
    
    companies = []
    tech_stacks = ["fastapi-react-postgres", "nodejs-tailwind-mongo", "django-vue-mysql"]
    statuses = ["pending", "in_progress", "completed", "failed"]
    
    for i in range(count):
        companies.append(create_test_company(
            name=f"Company {i+1}",
            slug=random_slug(),
            user_id=random.choice(user_ids),
            tech_stack=random.choice(tech_stacks),
            status=random.choice(statuses)
        ))
    return companies


def generate_deployments(count: int = 10, company_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Generate multiple test deployments"""
    from tests.fixtures.deployments import create_test_deployment
    
    if company_ids is None:
        company_ids = [random_string(36) for _ in range(count)]
    
    deployments = []
    statuses = ["pending", "provisioning", "active", "stopped", "failed"]
    
    for i in range(count):
        deployments.append(create_test_deployment(
            company_id=random.choice(company_ids),
            subdomain=random_subdomain(),
            status=random.choice(statuses)
        ))
    return deployments


def generate_tickets(count: int = 10) -> List[Dict[str, Any]]:
    """Generate multiple test tickets"""
    tickets = []
    departments = ["Engineering", "Design", "DevOps", "QA", "Documentation"]
    priorities = ["low", "medium", "high", "critical"]
    statuses = ["pending", "in_progress", "completed", "blocked"]
    
    for i in range(count):
        tickets.append({
            "ticket_id": f"TKT-{random_string(6, string.ascii_uppercase + string.digits)}",
            "department": random.choice(departments),
            "title": f"Test Ticket {i+1}",
            "instruction": f"This is a test instruction for ticket {i+1}",
            "status": random.choice(statuses),
            "priority": random.choice(priorities),
            "assigned_to": f"worker-{random.randint(1, 5)}",
            "created_at": random_datetime().isoformat(),
        })
    return tickets


def generate_api_keys(count: int = 5) -> List[str]:
    """Generate test API keys"""
    return [f"sk_test_{random_string(32, string.ascii_letters + string.digits)}" for _ in range(count)]


def generate_jwt_token() -> str:
    """Generate a fake JWT token for testing"""
    header = random_string(20, string.ascii_letters + string.digits)
    payload = random_string(40, string.ascii_letters + string.digits)
    signature = random_string(30, string.ascii_letters + string.digits)
    return f"{header}.{payload}.{signature}"

# Made with Bob
