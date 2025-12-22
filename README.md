# PDF Data Extraction with Gemini AI API

## 📌 Project Overview
This project asynchronously extracts and processes decision data from PDFs on the **Ministry of Communication and Information Technology (MOCIT), Nepal** website using the **Google Gemini AI API**. It scrapes paginated content, downloads PDFs, processes them with AI, and stores structured data in JSON format.

## 🚀 Features
- **Asynchronous Web Scraping** using `aiohttp`
- **PDF Download & Processing** with AI-powered data extraction
- **Resumable Progress Tracking** (progress.txt, processed_pdfs.txt)
- **Structured JSON Output** with Pydantic validation
- **Unit & Integration Tests** with pytest
- **Error Handling & Rate Limiting** built-in

## 📁 Project Structure
```
├── main.py              # Main async orchestration script
├── scraper.py           # Async web scraping & PDF handling
├── models.py            # Pydantic data model (Decision)
├── conftest.py          # Pytest fixtures & mocks
├── test_all.py          # Mock-based unit tests
├── test_actual.py       # Real HTTP/API integration tests
├── requirements.txt     # Python dependencies
├── .gitignore          # Ignored files (env, temp files, etc.)
├── progress.txt         # Tracks last processed page (auto-generated)
├── processed_pdfs.txt   # Tracks processed PDFs (auto-generated)
└── all_decisions.json   # Final output (auto-generated) 
```

## ⚙️ Prerequisites
- Python 3.8+
- Google Gemini API Key ([Get it here](https://aistudio.google.com/app/apikey))

## 🔧 Installation
1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd <project-folder>
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   - Create a `.env` file in the project root
   - Add your Gemini API key:
     ```
     GEMINI_API_KEY=your_api_key_here
     ```

## 🏃 Usage
Run the main script (asynchronous version):
```bash
python main.py
```

### Key Commands:
- **Run tests (mock-based)**:
  ```bash
  pytest test_all.py -v
  ```
- **Run real integration tests** (requires API key and internet):
  ```bash
  pytest test_actual.py -v
  ```
- **Clean temporary files**:
  ```bash
  del temp_*.pdf  # Windows
  # or
  rm temp_*.pdf   # Linux/Mac
  ```

## 📊 Output
- `all_decisions.json` – Contains extracted decision data with:
  - `source`: Unique PDF identifier
  - `serial_number`: Sequential ID per PDF
  - `ministry`: Ministry name (Nepali)
  - `decision_summary`: Brief summary (Nepali)

## 🧪 Testing
- **Mock Tests** (`test_all.py`): Fast, offline unit tests using mock
- **Real Tests** (`test_actual.py`): Live HTTP and API tests (requires internet & API key)

## ⚠️ Notes
- The script is **resumable**: It tracks processed pages and PDFs.
- Temporary PDFs are deleted after processing.
- Ensure `GEMINI_API_KEY` is set in environment or `.env` file.
- Rate limits and network errors are handled with retries/logging.

## 🗂️ Synchronous Version
A synchronous version is also available in the codebase but is **not the primary focus**. It follows similar logic but without async/await patterns. Use it only if async is not feasible for your environment.
