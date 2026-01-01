import os
from dotenv import load_dotenv
import json
from google import genai
from pydantic import BaseModel, Field
from typing import List
import csv

# Load environment variables from .env file
load_dotenv()

# Set the Gemini API key from environment variables
genai.api_key = os.getenv("GEMINI_API_KEY")

# Define the data model for the decisions
class Decision(BaseModel):
    """A single decision made by the Council of Ministers, extracted from the PDF."""
    serial_number: int = Field(description="The serial number of the decision as an integer.")
    ministry: str = Field(description="The name of the responsible ministry in Nepali.")
    decision_summary: str = Field(description="A brief summary of the decision in Nepali.")

# Path to the PDF file to be processed
PDF_FILE_PATH = "pdf1.pdf"

# Function to extract structured data from PDF
def extract_structured_data_from_pdf(pdf_path: str) -> List[dict] | None:
    """
    Uploads a PDF and uses the Gemini API to extract data adhering to the Pydantic schema.
    """
    uploaded_file = None
    try:
        # Automatically finds the GEMINI_API_KEY from your environment.
        client = genai.Client()

        # Upload the PDF file
        print(f"Uploading file: {pdf_path}...")
        uploaded_file = client.files.upload(file=pdf_path)
        print(f"File uploaded successfully: {uploaded_file.name}")

        # Define the detailed prompt
        prompt = (
            "Analyze the attached PDF file, which contains a list of Council of Ministers decisions. "
            "Extract the data for all decisions strictly following the provided JSON schema. "
            "Ensure the output is a single JSON array containing all entries."
        )

        # Generate the JSON schema for the list of Decision objects
        response_schema = {
            "type": "array",
            "items": Decision.model_json_schema()
        }

        # Call the model with the file, prompt, and structured output config
        print("Generating structured content...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, uploaded_file],
            config=genai.types.GenerateContentConfig(
                # Crucial lines for structured output:
                response_mime_type="application/json",
                response_schema=response_schema,
            ),
        )
        return json.loads(response.text)

    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    finally:
        # Clean up: Delete the uploaded file from the server (they expire after 48 hours anyway)
        if uploaded_file:
            print(f"Deleting uploaded file: {uploaded_file.name}...")
            client.files.delete(name=uploaded_file.name)

def save_data_to_csv(data: List[dict], filename: str = "output.csv"):
    """
    Saves the extracted data (list of dicts) to a CSV file.
    """
    if not data:
        print("No data to save.")
        return
    # Get fieldnames from the first dict (assumes all dicts have the same keys)
    fieldnames = data[0].keys()
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()  # Write column headers
        writer.writerows(data)  # Write the data rows
    print(f"Data successfully saved to {filename}")

if __name__ == "__main__":
    if not os.path.exists(PDF_FILE_PATH):
        print(f"Error: The file '{PDF_FILE_PATH}' was not found. Please ensure it is in the same directory.")
    elif "GEMINI_API_KEY" not in os.environ:
        print("Error: The GEMINI_API_KEY environment variable is not set.")
        print("Please set it before running the script.")
    else:
        # Extract the data
        extracted_data = extract_structured_data_from_pdf(PDF_FILE_PATH)

        if extracted_data:
            # Save to JSON file
            with open("output.json", "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            print("Data successfully extracted and saved to output.json")
        else:
            print("Failed to extract data.")



