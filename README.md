# PDF Decision Extraction (Gemini + Async Scraper)

## Overview
This project scrapes decision documents from Nepal MOCIT pages, downloads PDFs, extracts structured decisions with Gemini, cleans the data, and stores it in JSON.

It includes:
- `async-await/`: primary async pipeline (recommended)
- `synchronous/`: simpler synchronous reference version

## Repository Layout
- `async-await/src/main.py`: orchestration (scrape, download, extract, clean, save)
- `async-await/src/scraper.py`: page parsing, PDF discovery, download, LLM extraction
- `async-await/src/models.py`: Pydantic schema for extracted decisions
- `async-await/src/data_cleaning.py`: post-processing and deduplication
- `async-await/test/`: mock and real integration tests
- `synchronous/main.py`: single-file synchronous workflow
- `requirement.txt`: Python dependencies

## Prerequisites
- Python 3.10+
- Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

## Setup
```bash
python -m venv myenv
myenv\Scripts\activate
pip install -r requirement.txt
```

Create `.env` in project root:
```env
GEMINI_API_KEY=your_api_key_here
```

## Run (Async Pipeline)
```bash
cd async-await
python -m src.main
```

Generated files:
- `async-await/all_decisions.json`
- `async-await/progress.txt`
- `async-await/processed_pdfs.txt`

## Run Tests
From `async-await/`:
```bash
pytest test/test_mock.py -v
```

Real/integration tests (network + API key required):
```bash
pytest test/test_real.py -v
```

## Notes
- The async pipeline is resumable via `progress.txt` and `processed_pdfs.txt`.
- Temporary PDFs are deleted after successful processing.
- Real tests may be flaky if source pages or PDF links change.
