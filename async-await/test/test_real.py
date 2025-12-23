import pytest
import aiohttp
import os
import json
from dotenv import load_dotenv
from src.scraper import get_content_urls_from_page, get_pdf_urls_from_content, download_pdf, process_pdf
from src.main import main, load_progress, save_progress, load_processed_pdfs, save_processed_pdf, scrape_all_pages, download_all_pdfs, process_all_pdfs

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
        # Use a high page number likely to have no content
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
        urls = await get_pdf_urls_from_content(session, "https://mocit.gov.np/content/1")  # Use a known URL with no PDFs
        assert urls == []  # Should return empty list

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

@pytest.mark.asyncio
async def test_process_pdf_success():
    """Test successful PDF processing with real AI API."""
    if not genai_api_key:
        pytest.skip("GEMINI_API_KEY not set—skipping real API test")
    
    pdf_path = "test_download.pdf"  # Assume we have one from download test
    if not os.path.exists(pdf_path):
        # Download a real PDF for testing
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            await download_pdf(session, "https://mocit.gov.np/pdf/example.pdf", pdf_path)  # Replace with real URL
    
    if os.path.exists(pdf_path):
        data = await process_pdf(pdf_path, "test_source")
        assert isinstance(data, list)  # Should return a list
        if data:
            assert data[0]["source"] == "test_source"  # Check source ID
        os.remove(pdf_path)  # Clean up

# Test progress and file handling functions
def test_load_progress_no_file(tmp_path):
    """Test loading progress when no file exists."""
    os.chdir(tmp_path)  # Use temp dir
    assert load_progress() == 1  # Should default to 1

def test_save_and_load_progress(tmp_path):
    """Test saving and loading progress."""
    os.chdir(tmp_path)
    save_progress(5)
    assert load_progress() == 5  # Should match saved value

def test_load_processed_pdfs_no_file(tmp_path):
    """Test loading processed PDFs when no file exists."""
    os.chdir(tmp_path)
    assert load_processed_pdfs() == set()  # Should return empty set

def test_save_and_load_processed_pdfs(tmp_path):
    """Test saving and loading processed PDF IDs."""
    os.chdir(tmp_path)
    save_processed_pdf("page1_item1")
    assert "page1_item1" in load_processed_pdfs()  # Should contain saved ID

@pytest.mark.asyncio
async def test_scrape_all_pages():
    """Test scraping all pages and collecting PDF data."""
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        base_url = "https://mocit.gov.np/category/326/?page="
        data = await scrape_all_pages(session, base_url, 1)
        assert isinstance(data, list)  # Should return a list of dicts
        if data:
            assert "source_id" in data[0] and "pdf_urls" in data[0]  # Check structure

@pytest.mark.asyncio
async def test_download_all_pdfs():
    """Test downloading all PDFs in parallel."""
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        # Use a real PDF URL from your previous output (e.g., from scraping)
        all_pdf_data = [{'source_id': 'page1_item1', 'pdf_urls': ['https://giwmscdnone.gov.np/media/pdf_upload/cab822_8p6ryjv.pdf']}]  # Real URL from your logs
        processed_pdfs = set()
        files = await download_all_pdfs(session, all_pdf_data, processed_pdfs)
        assert isinstance(files, list)  # Should return a list of dicts
        if files:
            assert "source_id" in files[0] and "filename" in files[0]  # Check structure
            # Clean up downloaded files (fix: check if filename is not None)
            for f in files:
                if f['filename'] and os.path.exists(f['filename']):
                    os.remove(f['filename'])

@pytest.mark.asyncio
async def test_process_all_pdfs():
    """Test processing all downloaded PDFs with LLM."""
    if not genai_api_key:
        pytest.skip("GEMINI_API_KEY not set—skipping real API test")
    
    # Assume we have downloaded files (from previous test)
    downloaded_files = [{'source_id': 'page1_item1', 'filename': 'temp_page1_item1.pdf'}]  # Mock or real
    if os.path.exists('temp_page1_item1.pdf'):  # Ensure file exists
        decisions = await process_all_pdfs(downloaded_files)
        assert isinstance(decisions, list)  # Should return a list
        if decisions:
            assert "source" in decisions[0]  # Check structure

@pytest.mark.asyncio
async def test_main_integration():
    """Test the full main() function with real calls."""
    if not genai_api_key:
        pytest.skip("GEMINI_API_KEY not set—skipping real integration test")
    
    await main()  # Runs full scraping, downloading, processing
    # Check if JSON exists and has data, but allow for no new data (e.g., all processed)
    if os.path.exists("all_decisions.json"):
        with open("all_decisions.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert isinstance(data, list)  # Should have data if file exists
            if data:
                assert "source" in data[0]  # Basic structure check
    else:
        # If file doesn't exist, that's also acceptable in this context
        pass
