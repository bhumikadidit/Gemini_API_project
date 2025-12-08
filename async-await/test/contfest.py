import pytest
import tempfile
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def temp_dir():
    """Provides a temporary directory for file tests."""
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp

@pytest.fixture
def mock_session():
    """Mocks aiohttp ClientSession for network requests."""
    session = AsyncMock()
    response = AsyncMock()
    response.status = 200
    response.text = AsyncMock(return_value="<html><div class='grid__card'><a href='/content/123/'>Link</a></div></html>")
    response.read = AsyncMock(return_value=b"fake pdf content")
    session.get.return_value.__aenter__.return_value = response
    return session

@pytest.fixture
def mock_genai_client():
    """Mocks Gemini client for API responses."""
    client = MagicMock()
    file_mock = MagicMock()
    file_mock.name = "test_file"
    client.files.upload.return_value = file_mock
    response_mock = MagicMock()
    response_mock.text = '[{"ministry": "Test Ministry", "decision_summary": "Test Summary"}]'
    client.models.generate_content.return_value = response_mock
    return client