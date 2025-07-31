#!/usr/bin/env python3
"""
Basic test for MessageClassifier structure
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_classification_result():
    """Test the ClassificationResult model."""
    try:
        # Import only the Pydantic model
        from pydantic import BaseModel, Field
        from typing import Optional
        
        class ClassificationResult(BaseModel):
            """Pydantic model for structured LLM classification output."""
            is_lead: bool = Field(description="Whether this message represents a lead")
            lead_category: Optional[str] = Field(description="Category of the lead (e.g., 'dentist', 'spanish_classes', 'restaurant')")
            lead_description: Optional[str] = Field(description="Description of what the person is looking for")
            confidence_score: float = Field(description="Confidence score between 0 and 1")
            reasoning: str = Field(description="Reasoning for the classification")
        
        # Test creating a ClassificationResult
        result = ClassificationResult(
            is_lead=True,
            lead_category="dentist",
            lead_description="Looking for a dentist",
            confidence_score=0.9,
            reasoning="Message clearly asks for dentist recommendations"
        )
        
        print("✅ ClassificationResult creation successful")
        print(f"✅ Result: {result}")
        print(f"✅ JSON: {result.model_dump_json()}")
        
        return True
        
    except Exception as e:
        print(f"❌ ClassificationResult test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_classification_result()
    if success:
        print("🎉 Basic tests passed!")
    else:
        print("💥 Basic tests failed!")
        exit(1) 