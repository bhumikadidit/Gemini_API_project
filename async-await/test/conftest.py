import pytest
import os
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

@pytest.fixture
def temp_dir(tmp_path, monkeypatch):
    """Use pytest's tmp_path for a temporary directory to avoid Windows permission errors."""
    original_cwd = os.getcwd()
    monkeypatch.chdir(tmp_path)  # Temporarily change to temp dir; monkeypatch restores it
    yield str(tmp_path)

class MockResponse:
    """Custom mock for aiohttp.ClientResponse that supports async context manager."""
    def __init__(self, status=200, text="<html></html>", content=b"fake content"):
        self.status = status
        self.text = AsyncMock(return_value=text)
        self.read = AsyncMock(return_value=content)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

@pytest.fixture
def mock_session():
    """Mocks aiohttp.ClientSession with proper async context manager support."""
    session = MagicMock()  # Use MagicMock for session.get to avoid coroutine issues
    
    # Default response
    response = MockResponse(
        status=200,
        text="<html><div class='grid__card'><a href='/content/123/'>Test</a></div></html>",
        content=b"fake pdf content"
    )
    
    # session.get returns the response instance directly (supports async with)
    session.get = MagicMock(return_value=response)
    
    return session

@pytest.fixture
def mock_genai_client():
    """Mocks Google Generative AI client."""
    client = MagicMock()
    
    uploaded_file = MagicMock()
    uploaded_file.name = "test_file.pdf"
    client.files.upload.return_value = uploaded_file
    
    response = MagicMock()
    response.text = '[{"ministry": "Test Ministry", "decision_summary": "Test decision"}]'
    client.models.generate_content.return_value = response
    
    client.files.delete.return_value = None
    
    return client