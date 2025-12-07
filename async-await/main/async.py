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

# Load environment variables
load_dotenv()
genai.api_key = os.getenv("GEMINI_API_KEY")

# Define the data model with source for unique identification
class Decision(BaseModel):
    source: str = Field(description="Unique identifier for the PDF source, e.g., 'page1_item1'")
    serial_number: str = Field(description="Unique serial number with source prefix, e.g., 'page1_item1_1'")
    ministry: str = Field(description="The name of the responsible ministry in Nepali.")
    decision_summary: str = Field(description="A brief summary of the decision in Nepali.")

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

# Async function to download a PDF
async def download_pdf(session, url, filename):
    async with session.get(url) as response:
        if response.status == 200:
            async with aiofiles.open(filename, 'wb') as f:
                await f.write(await response.read())
            return filename
    return None

# Async function to process a PDF and extract data
async def process_pdf(pdf_path, source_id):
    uploaded_file = None
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
        print(f"Error processing {pdf_path}: {e}")
        return []
    finally:
        if uploaded_file:
            client.files.delete(name=uploaded_file.name)

# Main async function
async def main():
    base_url = "https://mocit.gov.np/category/326/?page="
    page_num = 1
    all_decisions = []
      
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    async with aiohttp.ClientSession(headers=headers) as session:
        while True:
            page_url = f"{base_url}{page_num}"
            content_urls = await get_content_urls_from_page(session, page_url)
            if not content_urls:
                break
              
            for idx, content_url in enumerate(content_urls):
                pdf_urls = await get_pdf_urls_from_content(session, content_url)
                if pdf_urls:
                    source_id = f"page{page_num}_item{idx+1}"
                    for pdf_url in pdf_urls:
                        pdf_filename = f"temp_{source_id}.pdf"
                        downloaded = await download_pdf(session, pdf_url, pdf_filename)
                        if downloaded:
                            decisions = await process_pdf(downloaded, source_id)
                            all_decisions.extend(decisions)
                            os.remove(downloaded)
              
            page_num += 1
          
        if all_decisions:
            # Append to existing JSON if it exists
            existing_data = []
            if os.path.exists("all_decisions.json"):
                with open("all_decisions.json", 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            existing_data.extend(all_decisions)
            async with aiofiles.open("all_decisions.json", 'w', encoding='utf-8') as f:
                await f.write(json.dumps(existing_data, indent=2, ensure_ascii=False))
            print(f"Data appended to all_decisions.json. Total decisions: {len(existing_data)}")
        else:
            print("No new data extracted.")
# Run the async main
if __name__ == "__main__":
    if "GEMINI_API_KEY" not in os.environ:
        print("Error: GEMINI_API_KEY not set.")
    else:
        asyncio.run(main())
