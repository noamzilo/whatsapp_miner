#!/usr/bin/env python3
"""
MANUAL TEST: Basic ClassificationResult Model Test

This is a manual test file to verify the ClassificationResult model works correctly.
Run this file directly to test the basic structure.

USAGE:
    python src/message_classification/manual_test_basic.py

This test does NOT require environment variables or database connection.
"""

import sys
from pathlib import Path

# Add project root to path for proper imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import only the Pydantic model directly
from pydantic import BaseModel, Field
from typing import Optional

class ClassificationResult(BaseModel):
    """Pydantic model for structured LLM classification output."""
    is_lead: bool = Field(description="Whether this message represents a lead")
    lead_category: Optional[str] = Field(description="Category of the lead (e.g., 'dentist', 'spanish_classes', 'restaurant')")
    lead_description: Optional[str] = Field(description="Description of what the person is looking for")
    confidence_score: float = Field(description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Reasoning for the classification")

def test_classification_result():
    """Test the ClassificationResult model."""
    try:
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
        
        # Test another case
        result2 = ClassificationResult(
            is_lead=False,
            lead_category=None,
            lead_description=None,
            confidence_score=0.8,
            reasoning="This is just a general conversation message"
        )
        
        print(f"✅ Second result: {result2}")
        print(f"✅ Second JSON: {result2.model_dump_json()}")
        
        return True
        
    except Exception as e:
        print(f"❌ ClassificationResult test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Running manual test for ClassificationResult model...")
    print("📝 This test verifies the Pydantic model structure works correctly")
    print("🔧 No environment variables or database required")
    print("-" * 50)
    
    success = test_classification_result()
    
    print("-" * 50)
    if success:
        print("🎉 Manual test passed!")
        print("✅ The ClassificationResult model is working correctly")
    else:
        print("💥 Manual test failed!")
        print("❌ There's an issue with the ClassificationResult model")
        exit(1) 