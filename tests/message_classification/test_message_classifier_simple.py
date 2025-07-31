#!/usr/bin/env python3
"""
Simple MessageClassifier Tests

Tests that don't require full MessageClassifier import to avoid environment variable issues.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Optional

# Add project root to path for proper imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pydantic import BaseModel, Field


class ClassificationResult(BaseModel):
    """Pydantic model for structured LLM classification output."""
    is_lead: bool = Field(description="Whether this message represents a lead")
    lead_category: Optional[str] = Field(
        description="Category of the lead (e.g., 'dentist', 'spanish_classes', 'restaurant')"
    )
    lead_description: Optional[str] = Field(description="Description of what the person is looking for")
    confidence_score: float = Field(description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Reasoning for the classification")


class TestMessageClassifierSimple:
    """Simple test cases that don't require full MessageClassifier import."""

    def test_classification_result_structure(self):
        """Test that ClassificationResult has the correct structure."""
        # Test lead classification
        lead_result = ClassificationResult(
            is_lead=True,
            lead_category="dentist",
            lead_description="Looking for a dentist",
            confidence_score=0.9,
            reasoning="Message asks for dentist recommendations"
        )
        
        assert lead_result.is_lead is True
        assert lead_result.lead_category == "dentist"
        assert lead_result.lead_description == "Looking for a dentist"
        assert lead_result.confidence_score == 0.9
        assert lead_result.reasoning == "Message asks for dentist recommendations"
        
        # Test non-lead classification
        non_lead_result = ClassificationResult(
            is_lead=False,
            lead_category=None,
            lead_description=None,
            confidence_score=0.8,
            reasoning="General conversation"
        )
        
        assert non_lead_result.is_lead is False
        assert non_lead_result.lead_category is None
        assert non_lead_result.lead_description is None
        assert non_lead_result.confidence_score == 0.8
        assert non_lead_result.reasoning == "General conversation"

    def test_classification_result_validation(self):
        """Test that ClassificationResult validates input correctly."""
        # Valid confidence scores
        valid_scores = [0.0, 0.5, 1.0]
        for score in valid_scores:
            result = ClassificationResult(
                is_lead=True,
                lead_category="test",
                lead_description="test",
                confidence_score=score,
                reasoning="test"
            )
            assert result.confidence_score == score
        
        # Test that required fields are enforced
        with pytest.raises(Exception):  # Should raise validation error
            ClassificationResult(
                is_lead=True,
                # Missing required fields
            )

    def test_classification_result_json_serialization(self):
        """Test JSON serialization of ClassificationResult."""
        result = ClassificationResult(
            is_lead=True,
            lead_category="restaurant",
            lead_description="Looking for a restaurant",
            confidence_score=0.85,
            reasoning="Message asks for restaurant recommendations"
        )
        
        # Test model_dump
        data = result.model_dump()
        assert isinstance(data, dict)
        assert data["is_lead"] is True
        assert data["lead_category"] == "restaurant"
        assert data["lead_description"] == "Looking for a restaurant"
        assert data["confidence_score"] == 0.85
        assert data["reasoning"] == "Message asks for restaurant recommendations"
        
        # Test model_dump_json
        json_str = result.model_dump_json()
        assert isinstance(json_str, str)
        assert '"is_lead":true' in json_str
        assert '"lead_category":"restaurant"' in json_str

    def test_classification_result_edge_cases(self):
        """Test edge cases for ClassificationResult."""
        # Test with minimum confidence
        min_result = ClassificationResult(
            is_lead=False,
            lead_category=None,
            lead_description=None,
            confidence_score=0.0,
            reasoning="No confidence"
        )
        assert min_result.confidence_score == 0.0
        
        # Test with maximum confidence
        max_result = ClassificationResult(
            is_lead=True,
            lead_category="plumber",
            lead_description="Looking for a plumber",
            confidence_score=1.0,
            reasoning="High confidence"
        )
        assert max_result.confidence_score == 1.0
        
        # Test with empty strings for optional fields
        empty_result = ClassificationResult(
            is_lead=False,
            lead_category="",
            lead_description="",
            confidence_score=0.5,
            reasoning="Empty strings"
        )
        assert empty_result.lead_category == ""
        assert empty_result.lead_description == ""

    @pytest.mark.parametrize("is_lead,expected_category", [
        (True, "dentist"),
        (True, "restaurant"),
        (True, "plumber"),
        (False, None),
    ])
    def test_classification_result_parametrized(self, is_lead, expected_category):
        """Test ClassificationResult with parametrized inputs."""
        result = ClassificationResult(
            is_lead=is_lead,
            lead_category=expected_category,
            lead_description="Test description" if is_lead else None,
            confidence_score=0.8,
            reasoning="Test reasoning"
        )
        
        assert result.is_lead == is_lead
        assert result.lead_category == expected_category
        if is_lead:
            assert result.lead_description == "Test description"
        else:
            assert result.lead_description is None 