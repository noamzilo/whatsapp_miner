"""
Pydantic models for message classification with centralized validation.

All models are validated at load time to ensure every field has a description.
This validation happens automatically when the module is imported - no manual calls needed.
"""

from src.message_classification.pydantic_models.lead_decision import LeadDecision

# Centralized validation happens automatically at import time
# All models are validated to have descriptions for every field
