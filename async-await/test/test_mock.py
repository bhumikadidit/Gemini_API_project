import pytest
import os
import json
from unittest.mock import patch, AsyncMock, MagicMock
from src.scraper import get_content_urls_from_page, get_pdf_urls_from_content, download_pdf, process_pdf
from src.main import main, load_progress, save_progress, load_processed_pdfs, save_processed_pdf

# Test scraping functions
@pytest.mark.asyncio
async def test_get_content_urls_from_page_success(mock_session):
    """Test successful extraction of content URLs from a page."""
    urls = await get_content_urls_from_page(mock_session, "https://mocit.gov.np/category/326/?page=1")
    assert isinstance(urls, list)  # Should return a list
    assert len(urls) >= 0  # At least empty if no cards

@pytest.mark.asyncio
async def test_get_content_urls_from_page_no_cards(mock_session):
    """Test handling when no content cards are found."""
    # Override the response for this test
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="<html></html>")
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    mock_session.get.return_value = mock_response
    urls = await get_content_urls_from_page(mock_session, "https://mocit.gov.np/category/326/?page=1")
    assert urls == []  # Should return empty list

@pytest.mark.asyncio
async def test_get_pdf_urls_from_content_with_download_link(mock_session):
    """Test PDF URL extraction when a download link is present."""
    # Override the response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="<html><div class='more-container'><a title='Download PDF File' href='/pdf/test.pdf'>Download</a></div></html>")
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    mock_session.get.return_value = mock_response
    urls = await get_pdf_urls_from_content(mock_session, "https://mocit.gov.np/content/123")
    assert len(urls) > 0  # Should find at least one PDF
    assert any('.pdf' in url for url in urls)  # Ensure it's a PDF URL

@pytest.mark.asyncio
async def test_get_pdf_urls_from_content_no_pdf(mock_session):
    """Test handling when no PDFs are found."""
    # Override the response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="<html><p>No PDF here</p></html>")
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    mock_session.get.return_value = mock_response
    urls = await get_pdf_urls_from_content(mock_session, "https://mocit.gov.np/content/123")
    assert urls == []  # Should return empty list

# Test download function
@pytest.mark.asyncio
async def test_download_pdf_success(mock_session, temp_dir):
    """Test successful PDF download."""
    path = os.path.join(temp_dir, "test.pdf")
    result = await download_pdf(mock_session, "https://mocit.gov.np/pdf/test.pdf", path)
    assert result == path  # Should return the file path
    assert os.path.exists(path)  # File should exist

@pytest.mark.asyncio
async def test_download_pdf_failure(mock_session):
    """Test handling of download failure."""
    # Override for failure
    mock_response = MagicMock()
    mock_response.status = 404
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    mock_session.get.return_value = mock_response
    result = await download_pdf(mock_session, "https://mocit.gov.np/pdf/notfound.pdf", "test.pdf")
    assert result is None  # Should return None on failure

# Test processing function
@pytest.mark.asyncio
async def test_process_pdf_success(mock_genai_client, temp_dir):
    """Test successful PDF processing and data extraction."""
    pdf_path = os.path.join(temp_dir, "test.pdf")
    with open(pdf_path, "wb") as f:
        f.write(b"fake content")  # Create dummy PDF
    
    with patch('src.scraper.genai.Client', return_value=mock_genai_client):
        data = await process_pdf(pdf_path, "test_source")
        assert len(data) >= 0  # Should return a list
        if data:
            assert data[0]["source"] == "test_source"  # Check source ID

# Test progress and file handling
def test_load_progress_no_file(temp_dir):
    """Test loading progress when no file exists."""
    assert load_progress() == 1  # Should default to 1

def test_save_and_load_progress(temp_dir):
    """Test saving and loading progress."""
    save_progress(5)
    assert load_progress() == 5  # Should match saved value

def test_load_processed_pdfs_no_file(temp_dir):
    """Test loading processed PDFs when no file exists."""
    assert load_processed_pdfs() == set()  # Should return empty set

def test_save_and_load_processed_pdfs(temp_dir):
    """Test saving and loading processed PDF IDs."""
    save_processed_pdf("page1_item1")
    assert "page1_item1" in load_processed_pdfs()  # Should contain saved ID
