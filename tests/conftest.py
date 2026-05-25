import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from backend.main import app


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    from tests.utils.test_helpers import create_mock_database_session
    return create_mock_database_session()


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for agent testing"""
    from tests.utils.test_helpers import create_mock_llm_client
    return create_mock_llm_client()


@pytest.fixture
def test_user():
    """Single test user"""
    from tests.fixtures.users import create_test_user
    return create_test_user()


@pytest.fixture
def test_admin():
    """Single test admin user"""
    from tests.fixtures.users import create_admin_user
    return create_admin_user()


@pytest.fixture
def test_users():
    """Multiple test users"""
    from tests.fixtures.users import TEST_USERS
    return TEST_USERS


@pytest.fixture
def test_company():
    """Single test company"""
    from tests.fixtures.companies import create_test_company
    return create_test_company()


@pytest.fixture
def test_companies():
    """Multiple test companies"""
    from tests.fixtures.companies import TEST_COMPANIES
    return TEST_COMPANIES


@pytest.fixture
def test_deployment():
    """Single test deployment"""
    from tests.fixtures.deployments import create_test_deployment
    return create_test_deployment()


@pytest.fixture
def test_deployments():
    """Multiple test deployments"""
    from tests.fixtures.deployments import TEST_DEPLOYMENTS
    return TEST_DEPLOYMENTS


@pytest.fixture
def mock_responses():
    """Mock API responses"""
    from tests.fixtures.mock_responses import (
        MOCK_LLM_RESPONSES,
        MOCK_STRIPE_RESPONSES,
        MOCK_GITHUB_RESPONSES,
        MOCK_HEALTH_RESPONSES
    )
    return {
        "llm": MOCK_LLM_RESPONSES,
        "stripe": MOCK_STRIPE_RESPONSES,
        "github": MOCK_GITHUB_RESPONSES,
        "health": MOCK_HEALTH_RESPONSES
    }


@pytest.fixture
def mock_stripe():
    """Mock Stripe API client"""
    with patch('stripe.Customer') as mock_customer, \
         patch('stripe.Subscription') as mock_subscription, \
         patch('stripe.checkout.Session') as mock_session:
        
        from tests.fixtures.mock_responses import MOCK_STRIPE_RESPONSES
        
        mock_customer.create.return_value = Mock(**MOCK_STRIPE_RESPONSES["create_customer"])
        mock_subscription.create.return_value = Mock(**MOCK_STRIPE_RESPONSES["create_subscription"])
        mock_session.create.return_value = Mock(**MOCK_STRIPE_RESPONSES["create_checkout_session"])
        
        yield {
            "customer": mock_customer,
            "subscription": mock_subscription,
            "session": mock_session
        }


@pytest.fixture
def mock_github():
    """Mock GitHub API client"""
    with patch('github.Github') as mock_gh:
        from tests.fixtures.mock_responses import MOCK_GITHUB_RESPONSES
        
        mock_repo = Mock()
        mock_repo.create_issue.return_value = Mock(**MOCK_GITHUB_RESPONSES["create_issue"])
        mock_repo.create_pull.return_value = Mock(**MOCK_GITHUB_RESPONSES["create_pr"])
        
        mock_gh.return_value.get_repo.return_value = mock_repo
        
        yield mock_gh


@pytest.fixture
def mock_s3():
    """Mock S3/MinIO client"""
    with patch('boto3.client') as mock_boto:
        mock_s3_client = Mock()
        mock_s3_client.upload_file.return_value = None
        mock_s3_client.download_file.return_value = None
        mock_s3_client.delete_object.return_value = {"DeleteMarker": True}
        mock_s3_client.generate_presigned_url.return_value = "https://example.com/presigned-url"
        
        mock_boto.return_value = mock_s3_client
        yield mock_s3_client


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch('redis.Redis') as mock_redis_class:
        mock_redis_client = Mock()
        mock_redis_client.get.return_value = None
        mock_redis_client.set.return_value = True
        mock_redis_client.delete.return_value = 1
        mock_redis_client.exists.return_value = False
        
        mock_redis_class.return_value = mock_redis_client
        yield mock_redis_client


@pytest.fixture
def mock_celery():
    """Mock Celery task queue"""
    with patch('celery.Celery') as mock_celery_class:
        mock_celery_app = Mock()
        mock_task = Mock()
        mock_task.delay.return_value = Mock(id="task-123", state="PENDING")
        
        mock_celery_app.task.return_value = lambda f: f
        mock_celery_app.send_task.return_value = mock_task.delay.return_value
        
        mock_celery_class.return_value = mock_celery_app
        yield mock_celery_app


@pytest.fixture
def mock_ollama():
    """Mock Ollama LLM service"""
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post:
        
        # Mock health check
        mock_get.return_value = Mock(status_code=200, json=lambda: {"models": []})
        
        # Mock chat completion
        from tests.fixtures.mock_responses import MOCK_LLM_RESPONSES
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "message": MOCK_LLM_RESPONSES["code_generation"]
            }
        )
        
        yield {"get": mock_get, "post": mock_post}


@pytest.fixture
def temp_dir(tmp_path):
    """Temporary directory for test files"""
    return tmp_path


@pytest.fixture
def cleanup_files():
    """Cleanup test files after test"""
    files_to_cleanup = []
    
    def register_file(filepath):
        files_to_cleanup.append(filepath)
    
    yield register_file
    
    # Cleanup
    import os
    for filepath in files_to_cleanup:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass


@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment variables after each test"""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "requires_llm: Tests that require LLM service")
    config.addinivalue_line("markers", "requires_db: Tests that require database")

# Made with Bob
