from pydantic import BaseModel, Field

# Define the data model with source for unique identification
class Decision(BaseModel):
    source: str = Field(description="Unique identifier for the PDF source, e.g., 'page1_item1'")
    serial_number: str = Field(description="Unique serial number with source prefix, e.g., 'page1_item1_1'")
    ministry: str = Field(description="The name of the responsible ministry in Nepali.")
    decision_summary: str = Field(description="A brief summary of the decision in Nepali.")