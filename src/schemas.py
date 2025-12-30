from pydantic import BaseModel, Field
from typing import Optional, Literal
from typing import Optional, Literal

class EmailExtraction(BaseModel):
    """
    Extracts structured data from supply chain emails to trigger SOPs.
    """
    part_id: Optional[str] = Field(None, description="The Part Number (e.g., P300)")
    order_id: Optional[str] = Field(None, description="The PO Number (e.g., O5007)")
    
    intent: Literal[
        "DELAY", 
        "PRICE_CHANGE", 
        "QUALITY_ALERT", 
        "CANCELLATION", 
        "DISCONTINUATION", 
        "PARTIAL_SHIPMENT", 
        "NEW_PROPOSAL",
        "DEMAND_CHANGE",
        "OTHER"
    ] = Field(..., description="The primary category of the email.")

    risk_score: int = Field(..., description="1 (Low) to 5 (Critical Line Stop)")
    
    # --- NEW FIELDS FOR ACTIONABLE DATA ---
    old_value: Optional[str] = Field(None, description="The previous date/price/qty (e.g. '2025-03-20' or '$78.50')")
    new_value: Optional[str] = Field(None, description="The new date/price/qty (e.g. '2025-04-05' or '$85.00')")
    tracking_number: Optional[str] = Field(None, description="If shipping, the tracking #")
    reasoning: str = Field(..., description="Why is this risk level assigned?")