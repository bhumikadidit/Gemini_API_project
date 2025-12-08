import pytest
import os
import json
from unittest.mock import patch, AsyncMock
from src.scraper import get_content_urls_from_page, get_pdf_urls_from_content, download_pdf, process_pdf
from src.main import main, load_progress, save_progress, load_processed_pdfs, save_processed_pdf

@pytest.mark.asyncio
async def test_get_content_urls_from_page_success(mock_session):
    urls = await get_content_urls_from_page(mock_session, "https://example.com/page=1")
    assert len(urls) == 1
    assert "https://mocit.gov.np/content/123/" in urls

@pytest.mark.asyncio
async def test_get_content_urls_from_page_no_cards(mock_session):
    mock_session.get.return_value.__aenter__.return_value.text = AsyncMock(return_value="<html></html>")
    urls = await get_content_urls_from_page(mock_session, "https://example.com/page=1")
    assert urls == []

@pytest.mark.asyncio
async def test_get_pdf_urls_from_content_with_download_link(mock_session):
    mock_session.get.return_value.__aenter__.return_value.text = AsyncMock(return_value="<html><div class='more-container'><a title='Download PDF File' href='/pdf/test.pdf'>Download</a></div></html>")
    urls = await get_pdf_urls_from_content(mock_session, "https://example.com/content/123")
    assert urls == ["https://mocit.gov.np/pdf/test.pdf"]

@pytest.mark.asyncio
async def test_get_pdf_urls_from_content_no_pdf(mock_session):
    mock_session.get.return_value.__aenter__.return_value.text = AsyncMock(return_value="<html><p>No PDF here</p></html>")
    urls = await get_pdf_urls_from_content(mock_session, "https://example.com/content/123")
    assert urls == []

@pytest.mark.asyncio
async def test_download_pdf_success(mock_session, temp_dir):
    path = os.path.join(temp_dir, "test.pdf")
    result = await download_pdf(mock_session, "https://example.com/pdf", path)
    assert result == path
    assert os.path.exists(path)

@pytest.mark.asyncio
async def test_download_pdf_failure(mock_session):
    mock_session.get.return_value.__aenter__.return_value.status = 404
    result = await download_pdf(mock_session, "https://example.com/pdf", "test.pdf")
    assert result is None

@pytest.mark.asyncio
async def test_process_pdf_success(mock_genai_client, temp_dir):
    pdf_path = os.path.join(temp_dir, "test.pdf")
    with open(pdf_path, "wb") as f:
        f.write(b"fake content")
    
    with patch('src.scraper.genai.Client', return_value=mock_genai_client):
        data = await process_pdf(pdf_path, "test_source")
        assert len(data) == 1
        assert data[0]["source"] == "test_source"
        assert data[0]["serial_number"] == "test_source_1"

def test_load_progress_no_file(temp_dir):
    os.chdir(temp_dir)
    assert load_progress() == 1

def test_save_and_load_progress(temp_dir):
    os.chdir(temp_dir)
    save_progress(5)
    assert load_progress() == 5

def test_load_processed_pdfs_no_file(temp_dir):
    os.chdir(temp_dir)
    assert load_processed_pdfs() == set()

def test_save_and_load_processed_pdfs(temp_dir):
    os.chdir(temp_dir)
    save_processed_pdf("page1_item1")
    assert "page1_item1" in load_processed_pdfs()

@pytest.mark.asyncio
async def test_main_integration(mock_session, mock_genai_client, temp_dir, monkeypatch):
    os.chdir(temp_dir)
    monkeypatch.setattr('src.main.aiohttp.ClientSession', lambda headers: mock_session)
    
    with patch('src.main.genai.Client', return_value=mock_genai_client):
        def mock_get(url):
            resp = AsyncMock()
            if "page=1" in url:
                resp.status = 200
                resp.text = AsyncMock(return_value="<html><div class='grid__card'><a href='/content/123/'>Test</a></div></html>")
            else:
                resp.status = 404
            return resp
        mock_session.get.side_effect = mock_get
        
        await main()
        
        assert os.path.exists("all_decisions.json")
        with open("all_decisions.json", 'r') as f:
            data = json.load(f)
            assert len(data) > 0
            assert data[0]["source"] == "page1_item1"