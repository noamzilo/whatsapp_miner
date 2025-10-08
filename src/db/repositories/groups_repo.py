"""Repository for WhatsAppGroup database operations."""

from src.db.models.whatsapp_group import WhatsAppGroup


def create_or_get_group(session, whatsapp_group_id: str, group_name: str = "") -> int:
    """Create or get a group, returns group ID."""
    group = session.query(WhatsAppGroup).filter_by(whatsapp_group_id=whatsapp_group_id).first()
    if not group:
        group = WhatsAppGroup(
            whatsapp_group_id=whatsapp_group_id,
            group_name=group_name
        )
        session.add(group)
        session.flush()
    
    return group.id


def get_group_by_id(session, group_id: int):
    """Get group by ID."""
    return session.query(WhatsAppGroup).filter_by(id=group_id).first()


def get_group_by_whatsapp_id(session, whatsapp_group_id: str):
    """Get group by WhatsApp group ID."""
    return session.query(WhatsAppGroup).filter_by(whatsapp_group_id=whatsapp_group_id).first()
