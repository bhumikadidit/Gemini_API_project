import os
import asyncio
import aiohttp
import aiofiles
from dotenv import load_dotenv
import json
import re
from google import genai
from pydantic import BaseModel, Field
from typing import List
from bs4 import BeautifulSoup
from .models import Decision
import logging 

# Load environment variables
load_dotenv()
genai.api_key = os.getenv("GEMINI_API_KEY")

# Async function to get content URLs from a paginated page
async def get_content_urls_from_page(session, page_url):
    async with session.get(page_url) as response:
        if response.status != 200:
            return []
        html = await response.text()
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('div', class_='grid__card')
        urls = []
        for card in cards:
            link = card.find('a', href=True)
            if link and '/content/' in link['href'].strip():
                href = link['href'].strip()
                full_url = f"https://mocit.gov.np{href}" if not href.startswith('http') else href
                urls.append(full_url)
        return urls

# Async function to get PDF URLs from a content page (prioritize flipbook download link)
async def get_pdf_urls_from_content(session, content_url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    async with session.get(content_url, headers=headers) as response:
        if response.status != 200:
            return []
        html = await response.text()
        soup = BeautifulSoup(html, 'html.parser')
        pdf_urls = set()
        
        # Prioritize the flipbook download link (targeted and easy)
        more_container = soup.find('div', class_='more-container')
        if more_container:
            download_link = more_container.find('a', title="Download PDF File", href=True)
            if download_link and '.pdf' in download_link['href'].strip():
                href = download_link['href'].strip()
                full_url = href if href.startswith('http') else f"https://mocit.gov.np{href}"
                pdf_urls.add(full_url)
                print(f"Found targeted PDF from flipbook download: {full_url}")
                return list(pdf_urls)  # Return immediately if found
        
        # Fallback: Check other <a> tags for PDFs
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            if '.pdf' in href and 'download' in href.lower():  # Ensure it's a download link
                full_url = href if href.startswith('http') else f"https://mocit.gov.np{href}"
                pdf_urls.add(full_url)
        
        # Fallback: Check <script> for PDF variable
        for script in soup.find_all('script'):
            if script.string:
                match = re.search(r"var pdf = ['\"]([^'\"]+\.pdf)['\"];", script.string)
                if match:
                    pdf_url = match.group(1)
                    full_url = pdf_url if pdf_url.startswith('http') else f"https://mocit.gov.np{pdf_url}"
                    pdf_urls.add(full_url)
        
        print(f"Found {len(pdf_urls)} PDF(s) on {content_url}: {list(pdf_urls)}")
        return list(pdf_urls)

# Async function to download a PDF with enhanced retry logic
async def download_pdf(session, url, filename):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    async with aiofiles.open(filename, 'wb') as f:
                        await f.write(await response.read())
                    return filename
                else:
                    logging.warning(f"Download failed for {url}: HTTP {response.status} (attempt {attempt + 1}/{max_retries})")
        except Exception as e:
            logging.error(f"Error downloading {url}: {e} (attempt {attempt + 1}/{max_retries})")
        if attempt < max_retries - 1:
            delay = min(2 ** attempt, 10)  # Exponential backoff: 1s, 2s, 4s (capped at 10s)
            logging.info(f"Retrying {url} in {delay} seconds...")
            await asyncio.sleep(delay)
    logging.error(f"Giving up on {url} after {max_retries} attempts")
    return None 

# Async function to process a PDF and extract data with enhanced retry logic
async def process_pdf(pdf_path, source_id):
    uploaded_file = None
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client = genai.Client()
            uploaded_file = client.files.upload(file=pdf_path)
            prompt = (
                "Analyze the attached PDF file, which contains a list of Council of Ministers decisions. "
                "Extract the data for all decisions strictly following the provided JSON schema. "
                "Ensure the output is a single JSON array containing all entries."
            )
            response_schema = {"type": "array", "items": Decision.model_json_schema()}
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[prompt, uploaded_file],
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )
            raw_data = json.loads(response.text)
            processed_data = []
            for i, item in enumerate(raw_data, start=1):
                processed_data.append({
                    "source": source_id,
                    "serial_number": f"{source_id}_{i}",
                    "ministry": item.get("ministry", ""),
                    "decision_summary": item.get("decision_summary", "")
                })
            return processed_data
        except Exception as e:
            logging.error(f"Error processing {pdf_path}: {e} (attempt {attempt + 1}/{max_retries})")
        finally:
            if uploaded_file:
                client.files.delete(name=uploaded_file.name)
        if attempt < max_retries - 1:
            delay = min(2 ** attempt, 10)  # Exponential backoff: 1s, 2s, 4s
            logging.info(f"Retrying processing for {pdf_path} in {delay} seconds...")
            await asyncio.sleep(delay)
    logging.error(f"Giving up on processing {pdf_path} after {max_retries} attempts")
    return []