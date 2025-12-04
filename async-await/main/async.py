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

# Load environment variables
load_dotenv()
genai.api_key = os.getenv("GEMINI_API_KEY")

# Define the data model
class Decision(BaseModel):
    serial_number: int = Field(description="The serial number of the decision as an integer.")
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

# Async function to get PDF URL from a content page
async def get_pdf_url_from_content(session, content_url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    async with session.get(content_url, headers=headers) as response:
        if response.status != 200:
            return None
        html = await response.text()
        soup = BeautifulSoup(html, 'html.parser')
        # Check <a> tags for .pdf
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            if href.endswith('.pdf'):
                return href if href.startswith('http') else f"https://mocit.gov.np{href}"
        # Check <embed> or <iframe> for PDFs
        for tag in soup.find_all(['embed', 'iframe'], src=True):
            src = tag['src'].strip()
            if src.endswith('.pdf'):
                return src if src.startswith('http') else f"https://mocit.gov.np{src}"
    return None

# Async function to download a PDF
async def download_pdf(session, url, filename):
    async with session.get(url) as response:
        if response.status == 200:
            async with aiofiles.open(filename, 'wb') as f:
                await f.write(await response.read())
            return filename
    return None

# Async function to process a PDF
async def process_pdf(pdf_path, output_json_path):
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
        data = json.loads(response.text)
        async with aiofiles.open(output_json_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, indent=2, ensure_ascii=False))
        return True
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return False
    finally:
        if uploaded_file:
            client.files.delete(name=uploaded_file.name)

# Main async function
async def main():
    base_url = "https://mocit.gov.np/category/326/?page="
    page_num = 1
    all_pdf_tasks = []
      
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    async with aiohttp.ClientSession(headers=headers) as session:
        while True:
            page_url = f"{base_url}{page_num}"
            content_urls = await get_content_urls_from_page(session, page_url)
            if not content_urls:
                break
              
            for content_url in content_urls:
                pdf_url = await get_pdf_url_from_content(session, content_url)
                if pdf_url:
                    content_id = content_url.split('/')[-2]
                    pdf_filename = f"temp_{content_id}.pdf"
                    json_filename = f"output_{content_id}.json"
                      
                    download_task = download_pdf(session, pdf_url, pdf_filename)
                    all_pdf_tasks.append((download_task, pdf_filename, json_filename))
              
            page_num += 1
          
        if not all_pdf_tasks:
            print("No PDFs found to process. Check if content pages have PDFs or site structure changed.")
            return
          
        download_results = await asyncio.gather(*[task[0] for task in all_pdf_tasks])
          
        process_tasks = []
        for (_, pdf_file, json_path), result in zip(all_pdf_tasks, download_results):
            if result:
                process_tasks.append(process_pdf(result, json_path))
          
        await asyncio.gather(*process_tasks)
          
        for _, downloaded_file, _ in all_pdf_tasks:
            if os.path.exists(downloaded_file):
                os.remove(downloaded_file)
      
    print("All PDFs processed and saved to JSON files.")

# Run the async main
if __name__ == "__main__":
    if "GEMINI_API_KEY" not in os.environ:
        print("Error: GEMINI_API_KEY not set.")
    else:
        asyncio.run(main())
