"""Repository for DetectedLead database operations."""

from src.db.models.detected_lead import DetectedLead


def create_lead_record(session, classification_id: int, user_id: int, 
                      group_id: int, lead_for: str, message_id: int = None, 
                      lead_category_id: int = None) -> int:
    """Create a lead record."""
    lead = DetectedLead(
        classification_id=classification_id,
        user_id=user_id,
        group_id=group_id,
        lead_for=lead_for,
        message_id=message_id,
        lead_category_id=lead_category_id
    )
    session.add(lead)
    session.flush()
    
    return lead.id


def get_lead_by_id(session, lead_id: int):
    """Get lead by ID."""
    return session.query(DetectedLead).filter_by(id=lead_id).first()


def get_total_leads_count(session):
    """Get total number of leads in database."""
    return session.query(DetectedLead).count()


def get_leads_count(session):
    """Get count of leads."""
    return session.query(DetectedLead).count()


def get_all_leads(session):
    """Get all leads."""
    return session.query(DetectedLead).all()


def delete_all_leads(session):
    """Delete all leads."""
    return session.query(DetectedLead).delete()
