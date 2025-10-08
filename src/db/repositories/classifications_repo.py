"""Repository for MessageIntentClassification database operations."""

from typing import Dict, Any
from src.db.models.message_intent_classification import MessageIntentClassification


def create_classification_record(session, message_id: int, prompt_template_id: int,
                               parsed_type_id: int, lead_category_id: int,
                               raw_llm_output: Dict[str, Any]) -> int:
    """Create a classification record."""
    classification = MessageIntentClassification(
        message_id=message_id,
        prompt_template_id=prompt_template_id,
        parsed_type_id=parsed_type_id,
        lead_category_id=lead_category_id,
        raw_llm_output=raw_llm_output
    )
    session.add(classification)
    session.flush()
    
    return classification.id


def get_all_classifications(session):
    """Get all classifications."""
    return session.query(MessageIntentClassification).all()


def get_all_classifications_count(session):
    """Get total number of classifications."""
    return session.query(MessageIntentClassification).count()


def delete_all_classifications(session):
    """Delete all classifications."""
    return session.query(MessageIntentClassification).delete()


def get_classifications_count(session):
    """Get count of classifications."""
    return session.query(MessageIntentClassification).count()
