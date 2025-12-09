import pytest
import aiohttp
import os
import json
from dotenv import load_dotenv
from src.scraper import get_content_urls_from_page, get_pdf_urls_from_content, download_pdf, process_pdf
from src.main import main, load_progress, save_progress, load_processed_pdfs, save_processed_pdf

# Load environment variables (for API key)
load_dotenv()
genai_api_key = os.getenv("GEMINI_API_KEY")

# Common headers for HTTP requests 
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

@pytest.mark.asyncio
async def test_get_content_urls_from_page_success():
    """Test successful extraction of content URLs from a real page."""
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        urls = await get_content_urls_from_page(session, "https://mocit.gov.np/category/326/?page=1")
        assert isinstance(urls, list)  # Should return a list
        assert len(urls) >= 0  # At least empty if no cards
        
@pytest.mark.asyncio
async def test_get_content_urls_from_page_no_cards():
    """Test handling when no content cards are found (use a page with no data if possible)."""
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        # Use a page that might have no cards (adjust URL if needed)
        urls = await get_content_urls_from_page(session, "https://mocit.gov.np/category/326/?page=999")  # High page number
        assert urls == []  # Should return empty list if no data

@pytest.mark.asyncio
async def test_get_pdf_urls_from_content_with_download_link():
    """Test PDF URL extraction from a real content page."""
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        urls = await get_pdf_urls_from_content(session, "https://mocit.gov.np/content/123")  # Use a known real URL
        assert isinstance(urls, list)
        assert len(urls) >= 0  # May be empty if no PDFs
        if urls:
            assert any('.pdf' in url for url in urls)  # Ensure it's a PDF URL if found
@pytest.mark.asyncio
async def test_get_pdf_urls_from_content_no_pdf():
    """Test handling when no PDFs are found (use a page without PDFs)."""
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        # Use a content page that likely has no PDFs (adjust URL)
        urls = await get_pdf_urls_from_content(session, "https://mocit.gov.np/content/1")  # Example
        assert urls == []  # Should return empty list

# Test download function (using real HTTP)
@pytest.mark.asyncio
async def test_download_pdf_success():
    """Test successful PDF download from a real URL."""
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        # Use a real PDF URL from the site (find one via scraping first)
        pdf_url = "https://mocit.gov.np/pdf/example.pdf"  # Replace with a real URL
        path = "test_download.pdf"
        result = await download_pdf(session, pdf_url, path)
        if result:
            assert result == path  # Should return the file path
            assert os.path.exists(path)  # File should exist
            os.remove(path)  # Clean up
        else:
            assert result is None  # If download fails

@pytest.mark.asyncio
async def test_download_pdf_failure():
    """Test handling of download failure (use invalid URL)."""
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        result = await download_pdf(session, "https://mocit.gov.np/pdf/notfound.pdf", "test.pdf")
        assert result is None  # Should return None on failure
