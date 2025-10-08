"""
LeadDecision Pydantic model for message classification results.

This model is automatically validated at load time to ensure all fields have descriptions.
"""

from typing import Optional
from pydantic import Field

from src.message_classification.pydantic_models.base import ValidatedBaseModel


class LeadDecision(ValidatedBaseModel):
    """
    Represents the classification result for a WhatsApp message.
    
    This model is validated at load time to ensure all fields have descriptions.
    """
    is_lead: bool = Field(
        description="Whether the message is a lead (purchase intent + clear business)"
    )
    business_type: Optional[str] = Field(
        default=None, 
        description="The business that can fulfill the need if is_lead=true"
    )


# Validation happens automatically when this module is imported
# No manual validation calls needed - it's built into the base class
