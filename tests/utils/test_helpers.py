"""
Test helper functions
"""
import json
from typing import Any, Dict, Optional
from unittest.mock import Mock, MagicMock


def create_mock_response(
    status_code: int = 200,
    json_data: Optional[Dict[str, Any]] = None,
    text: str = "",
    headers: Optional[Dict[str, str]] = None,
) -> Mock:
    """Create a mock HTTP response object"""
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data or {}
    mock_response.text = text or json.dumps(json_data or {})
    mock_response.headers = headers or {}
    mock_response.ok = 200 <= status_code < 300
    return mock_response


def create_mock_llm_client(responses: Optional[Dict[str, str]] = None) -> Mock:
    """Create a mock LLM client for testing agents"""
    mock_client = Mock()
    # Ensure responses is a dict, not None
    responses = responses or {}

    def mock_chat_completion(*args, **kwargs):
        messages = kwargs.get("messages", [])
        if messages:
            last_message = messages[-1].get("content", "")
            # Return appropriate response based on prompt
            if "ticket" in last_message.lower():
                return Mock(choices=[Mock(message=Mock(content=responses.get("ticket", "[]")))])
            elif "code" in last_message.lower():
                return Mock(choices=[Mock(message=Mock(content=responses.get("code", "# code")))])
        return Mock(choices=[Mock(message=Mock(content="Mock response"))])

    mock_client.chat.completions.create = mock_chat_completion
    return mock_client


def create_mock_database_session() -> Mock:
    """Create a mock database session"""
    mock_session = MagicMock()
    mock_session.query.return_value = mock_session
    mock_session.filter.return_value = mock_session
    mock_session.first.return_value = None
    mock_session.all.return_value = []
    mock_session.commit.return_value = None
    mock_session.rollback.return_value = None
    mock_session.close.return_value = None
    return mock_session


def assert_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID"""
    import uuid

    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def assert_valid_iso_datetime(value: str) -> bool:
    """Check if a string is a valid ISO datetime"""
    from datetime import datetime

    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except (ValueError, AttributeError):
        return False


def assert_response_structure(
    response: Dict[str, Any], required_fields: list, optional_fields: Optional[list] = None
) -> bool:
    """Validate response has required structure"""
    optional_fields = optional_fields or []

    # Check all required fields are present
    for field in required_fields:
        if field not in response:
            raise AssertionError(f"Required field '{field}' missing from response")

    # Check no unexpected fields (only required + optional)
    allowed_fields = set(required_fields + optional_fields)
    actual_fields = set(response.keys())
    unexpected = actual_fields - allowed_fields

    if unexpected:
        raise AssertionError(f"Unexpected fields in response: {unexpected}")

    return True


def mock_env_vars(env_dict: Dict[str, str]):
    """Context manager to temporarily set environment variables"""
    import os
    from unittest.mock import patch

    return patch.dict(os.environ, env_dict)


def create_temp_file(content: str, suffix: str = ".txt") -> str:
    """Create a temporary file with content and return its path"""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
        f.write(content)
        return f.name


def cleanup_temp_file(filepath: str):
    """Remove a temporary file"""
    import os

    try:
        os.remove(filepath)
    except FileNotFoundError:
        pass


# Made with Bob
