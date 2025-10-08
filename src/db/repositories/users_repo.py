"""Repository for WhatsAppUser database operations."""

from src.db.models.whatsapp_user import WhatsAppUser


def create_or_get_user(session, whatsapp_id: str, display_name: str = "") -> int:
    """Create or get a user, returns user ID."""
    user = session.query(WhatsAppUser).filter_by(whatsapp_id=whatsapp_id).first()
    if not user:
        user = WhatsAppUser(whatsapp_id=whatsapp_id, display_name=display_name)
        session.add(user)
        session.flush()
    
    return user.id


def get_user_by_id(session, user_id: int):
    """Get user by ID."""
    return session.query(WhatsAppUser).filter_by(id=user_id).first()


def get_user_by_whatsapp_id(session, whatsapp_id: str):
    """Get user by WhatsApp ID."""
    return session.query(WhatsAppUser).filter_by(whatsapp_id=whatsapp_id).first()
