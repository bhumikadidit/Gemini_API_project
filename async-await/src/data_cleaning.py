import logging
from typing import List, Dict

def clean_extracted_data(data: List[Dict]) -> List[Dict]:
    """
    Cleans and validates the extracted data from PDFs.
    """
    if not data:
        logging.warning("No data provided for cleaning.")
        return []
    
    cleaned_data = []
    seen_serials = set()  # To track duplicates
    
    for item in data:
        # Validate required fields
        required_fields = ['source', 'serial_number', 'ministry', 'decision_summary']
        missing_fields = [field for field in required_fields if field not in item or not item[field]]
        if missing_fields:
            logging.warning(f"Skipping item with missing/invalid fields: {missing_fields}. Item: {item}")
            continue  # Skip invalid items
        
        # Clean text fields
        item['ministry'] = item['ministry'].strip().lower()  # Standardize ministry names
        item['decision_summary'] = item['decision_summary'].strip()  # Remove extra spaces
        
        # Remove duplicates
        if item['serial_number'] in seen_serials:
            logging.info(f"Removing duplicate serial_number: {item['serial_number']}")
            continue
        seen_serials.add(item['serial_number'])
        
        cleaned_data.append(item)
    
    logging.info(f"Data cleaning complete: {len(cleaned_data)} valid items retained from {len(data)} original.")
    return cleaned_data