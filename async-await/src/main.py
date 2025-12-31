import os
import asyncio
import aiohttp
import aiofiles
from dotenv import load_dotenv
import json
from google import genai
from pydantic import BaseModel, Field
from typing import List
from bs4 import BeautifulSoup
import logging
from .scraper import get_content_urls_from_page, get_pdf_urls_from_content, download_pdf, process_pdf

# Load environment variables
load_dotenv()
genai.api_key = os.getenv("GEMINI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load progress from file
def load_progress():
    if os.path.exists('progress.txt'):
        with open('progress.txt', 'r') as f:
            return int(f.read().strip())
    return 1  # Start from page 1

# Save progress to file
def save_progress(page_num):
    with open('progress.txt', 'w') as f:
        f.write(str(page_num))

# Load processed PDFs
def load_processed_pdfs():
    if os.path.exists('processed_pdfs.txt'):
        with open('processed_pdfs.txt', 'r') as f:
            return set(line.strip() for line in f)
    return set()

# Save processed PDF
def save_processed_pdf(source_id):
    with open('processed_pdfs.txt', 'a') as f:
        f.write(source_id + '\n')

# Function to scrape all pages and collect PDF URLs
async def scrape_all_pages(session, base_url, start_page):
    all_pdf_data = []  # List of dicts: {'source_id': str, 'pdf_urls': list}
    page_num = start_page
    while True:
        page_url = f"{base_url}{page_num}"
        content_urls = await get_content_urls_from_page(session, page_url)
        if not content_urls:
            break
        
        for idx, content_url in enumerate(content_urls):
            source_id = f"page{page_num}_item{idx+1}"
            pdf_urls = await get_pdf_urls_from_content(session, content_url)
            if pdf_urls:
                all_pdf_data.append({'source_id': source_id, 'pdf_urls': pdf_urls})
        
        page_num += 1
    
    save_progress(page_num - 1)  # Save progress after scraping all
    return all_pdf_data

# Function to download all PDFs
async def download_all_pdfs(session, all_pdf_data, processed_pdfs):
    downloaded_files = []  # List of dicts: {'source_id': str, 'filename': str}
    tasks = []
    
    for data in all_pdf_data:
        source_id = data['source_id']
        if source_id in processed_pdfs:
            print(f"Skipping already processed: {source_id}")
            continue
        
        for pdf_url in data['pdf_urls']:
            pdf_filename = f"temp_{source_id}.pdf"
            tasks.append(download_pdf(session, pdf_url, pdf_filename))
    
    # Run downloads in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Download failed for task {i}: {result}")
        else:
            downloaded_files.append({'source_id': all_pdf_data[i]['source_id'], 'filename': result})
    
    return downloaded_files

# Function to process all PDFs with LLM
async def process_all_pdfs(downloaded_files):
    all_decisions = []
    for file_data in downloaded_files:
        source_id = file_data['source_id']
        filename = file_data['filename']
        decisions = await process_pdf(filename, source_id)
        all_decisions.extend(decisions)
        save_processed_pdf(source_id)
        os.remove(filename)  # Clean up
    
    return all_decisions

# Main async function
# Main async function
async def main():
    base_url = "https://mocit.gov.np/category/326/?page="
    start_page = load_progress()
    processed_pdfs = load_processed_pdfs()
    all_decisions = []
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    async with aiohttp.ClientSession(headers=headers) as session:
        #Scrape all pages
        logging.info(f"Phase 1: Starting to scrape pages from {start_page}...")
        all_pdf_data = await scrape_all_pages(session, base_url, start_page)
        logging.info(f"Phase 1: Completed scraping. Found {len(all_pdf_data)} PDF sources.")
        
        #Download all PDFs
        logging.info("Phase 2: Starting PDF downloads...")
        downloaded_files = await download_all_pdfs(session, all_pdf_data, processed_pdfs)
        logging.info(f"Phase 2: Completed downloads. Downloaded {len(downloaded_files)} files.")
        
        #Process all PDFs with LLM
        logging.info("Phase 3: Starting PDF processing with LLM...")
        all_decisions = await process_all_pdfs(downloaded_files)
        logging.info(f"Phase 3: Completed processing. Extracted {len(all_decisions)} decisions.")
        
        # Save final data
        if all_decisions:
            existing_data = []
            if os.path.exists("all_decisions.json"):
                with open("all_decisions.json", 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            existing_data.extend(all_decisions)
            async with aiofiles.open("all_decisions.json", 'w', encoding='utf-8') as f:
                await f.write(json.dumps(existing_data, indent=2, ensure_ascii=False))
            logging.info(f"Data appended to all_decisions.json. Total decisions: {len(existing_data)}")
        else:
            logging.info("No new data extracted.")

# Run the async main
if __name__ == "__main__":
    if "GEMINI_API_KEY" not in os.environ:
        print("Error: GEMINI_API_KEY not set.")
    else:
        asyncio.run(main())
