#!/usr/bin/env python3
"""
Test ClassificationResult Model

Tests for the ClassificationResult Pydantic model used in message classification.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path for proper imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pydantic import BaseModel, Field
from typing import Optional


class ClassificationResult(BaseModel):
    """Pydantic model for structured LLM classification output."""
    is_lead: bool = Field(description="Whether this message represents a lead")
    lead_category: Optional[str] = Field(
        description="Category of the lead (e.g., 'dentist', 'spanish_classes', 'restaurant')"
    )
    lead_description: Optional[str] = Field(description="Description of what the person is looking for")
    confidence_score: float = Field(description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Reasoning for the classification")


class TestClassificationResult:
    """Test cases for ClassificationResult model."""

    def test_create_lead_classification(self):
        """Test creating a ClassificationResult for a lead."""
        result = ClassificationResult(
            is_lead=True,
            lead_category="dentist",
            lead_description="Looking for a dentist",
            confidence_score=0.9,
            reasoning="Message clearly asks for dentist recommendations"
        )

        # Assertions
        assert result.is_lead is True
        assert result.lead_category == "dentist"
        assert result.lead_description == "Looking for a dentist"
        assert result.confidence_score == 0.9
        assert result.reasoning == "Message clearly asks for dentist recommendations"

    def test_create_non_lead_classification(self):
        """Test creating a ClassificationResult for a non-lead message."""
        result = ClassificationResult(
            is_lead=False,
            lead_category=None,
            lead_description=None,
            confidence_score=0.8,
            reasoning="This is just a general conversation message"
        )

        # Assertions
        assert result.is_lead is False
        assert result.lead_category is None
        assert result.lead_description is None
        assert result.confidence_score == 0.8
        assert result.reasoning == "This is just a general conversation message"

    def test_confidence_score_validation(self):
        """Test that confidence score is properly validated."""
        # Valid confidence score
        result = ClassificationResult(
            is_lead=True,
            lead_category="restaurant",
            lead_description="Looking for a restaurant",
            confidence_score=0.75,
            reasoning="Valid confidence score"
        )
        assert result.confidence_score == 0.75

        # Test edge cases
        result_min = ClassificationResult(
            is_lead=False,
            lead_category=None,
            lead_description=None,
            confidence_score=0.0,
            reasoning="Minimum confidence"
        )
        assert result_min.confidence_score == 0.0

        result_max = ClassificationResult(
            is_lead=True,
            lead_category="plumber",
            lead_description="Looking for a plumber",
            confidence_score=1.0,
            reasoning="Maximum confidence"
        )
        assert result_max.confidence_score == 1.0

    def test_json_serialization(self):
        """Test that ClassificationResult can be serialized to JSON."""
        result = ClassificationResult(
            is_lead=True,
            lead_category="spanish_classes",
            lead_description="Looking for Spanish classes",
            confidence_score=0.85,
            reasoning="Message asks for Spanish class recommendations"
        )

        json_str = result.model_dump_json()
        assert isinstance(json_str, str)
        
        # Parse back and verify
        import json
        data = json.loads(json_str)
        assert data["is_lead"] is True
        assert data["lead_category"] == "spanish_classes"
        assert data["lead_description"] == "Looking for Spanish classes"
        assert data["confidence_score"] == 0.85
        assert data["reasoning"] == "Message asks for Spanish class recommendations"

    def test_model_dump(self):
        """Test that ClassificationResult can be dumped to dict."""
        result = ClassificationResult(
            is_lead=False,
            lead_category=None,
            lead_description=None,
            confidence_score=0.6,
            reasoning="General conversation"
        )

        data = result.model_dump()
        assert isinstance(data, dict)
        assert data["is_lead"] is False
        assert data["lead_category"] is None
        assert data["lead_description"] is None
        assert data["confidence_score"] == 0.6
        assert data["reasoning"] == "General conversation"

    def test_optional_fields(self):
        """Test that optional fields work correctly."""
        # Test with all optional fields as None
        result = ClassificationResult(
            is_lead=False,
            lead_category=None,
            lead_description=None,
            confidence_score=0.5,
            reasoning="No lead detected"
        )
        assert result.lead_category is None
        assert result.lead_description is None

        # Test with some optional fields set
        result2 = ClassificationResult(
            is_lead=True,
            lead_category="electrician",
            lead_description=None,
            confidence_score=0.7,
            reasoning="Lead detected but no description"
        )
        assert result2.lead_category == "electrician"
        assert result2.lead_description is None 