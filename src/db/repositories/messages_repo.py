"""Repository for WhatsAppMessage database operations."""

from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import not_
from src.db.models.whatsapp_message import WhatsAppMessage
from src.db.models.whatsapp_user import WhatsAppUser
from src.db.models.whatsapp_group import WhatsAppGroup
from src.db.repositories.users_repo import create_or_get_user
from src.db.repositories.groups_repo import create_or_get_group


def create_message(session, message_id: str, sender_id: int, group_id: int, 
                  raw_text: str, message_type: str = "text", 
                  is_forwarded: bool = False, timestamp: Optional[datetime] = None,
                  is_real: bool = True) -> int:
    """Create a message, returns message ID. Ensures user and group exist."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    # Check if message already exists
    existing = session.query(WhatsAppMessage).filter_by(message_id=message_id).first()
    if existing:
        return existing.id
    
    # Validate that user exists
    user = session.query(WhatsAppUser).filter_by(id=sender_id).first()
    if not user:
        raise ValueError(f"User with ID {sender_id} does not exist")
    
    # Validate that group exists
    group = session.query(WhatsAppGroup).filter_by(id=group_id).first()
    if not group:
        raise ValueError(f"Group with ID {group_id} does not exist")
    
    message = WhatsAppMessage(
        message_id=message_id,
        sender_id=sender_id,
        group_id=group_id,
        timestamp=timestamp,
        raw_text=raw_text,
        message_type=message_type,
        is_forwarded=is_forwarded,
        llm_processed=False,
        is_real=is_real
    )
    session.add(message)
    session.flush()
    
    return message.id


def create_message_with_dependencies(session, message_id: str, whatsapp_user_id: str, 
                                   whatsapp_group_id: str, raw_text: str, 
                                   user_display_name: str = "", group_name: str = "",
                                   message_type: str = "text", is_forwarded: bool = False, 
                                   timestamp: Optional[datetime] = None, is_real: bool = True) -> int:
    """Create a message with automatic user and group creation. Atomic operation."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    # Check if message already exists
    existing = session.query(WhatsAppMessage).filter_by(message_id=message_id).first()
    if existing:
        return existing.id
    
    # Create or get user
    user_id = create_or_get_user(session, whatsapp_user_id, user_display_name)
    
    # Create or get group
    group_id = create_or_get_group(session, whatsapp_group_id, group_name)
    
    # Create the message
    return create_message(session, message_id, user_id, group_id, raw_text, 
                        message_type, is_forwarded, timestamp, is_real)


def create_fake_message_with_dependencies(session, message_text: str, 
                                        user_id: int = 1, group_id: int = 1,
                                        message_id: Optional[str] = None) -> int:
    """Create a fake message with proper user and group dependencies."""
    import uuid
    
    # Generate unique message ID if not provided
    if message_id is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        message_id = f"fake_msg_{timestamp}_{unique_id}"
    
    # Create fake user if it doesn't exist
    user_whatsapp_id = f"user{user_id}@c.us"
    user_display_name = f"Test User {user_id}"
    
    # Create fake group if it doesn't exist
    group_whatsapp_id = f"group{group_id}@g.us"
    group_name = f"Test Group {group_id}"
    
    # Use the atomic operation with is_real=False for fake messages
    return create_message_with_dependencies(
        session=session,
        message_id=message_id,
        whatsapp_user_id=user_whatsapp_id,
        whatsapp_group_id=group_whatsapp_id,
        raw_text=message_text,
        user_display_name=user_display_name,
        group_name=group_name,
        is_real=False  # Fake messages are not real
    )


def get_unclassified_messages(session):
    """Get all messages that haven't been classified yet, ordered by newest first."""
    return session.query(WhatsAppMessage).filter(
        not_(WhatsAppMessage.llm_processed)
    ).order_by(WhatsAppMessage.timestamp.desc()).all()


def mark_message_as_processed(session, message_id: int) -> None:
    """Mark a message as processed."""
    message = session.query(WhatsAppMessage).filter_by(id=message_id).first()
    if message:
        message.llm_processed = True
        # Note: commit is handled by the calling function


def get_message_by_id(session, message_id: int):
    """Get message by ID."""
    return session.query(WhatsAppMessage).filter_by(id=message_id).first()


def get_message_by_message_id(session, message_id: str):
    """Get message by message_id string."""
    return session.query(WhatsAppMessage).filter_by(message_id=message_id).first()


def update_messages_to_unprocessed(session):
    """Update all processed messages to unprocessed."""
    return session.query(WhatsAppMessage).filter(
        WhatsAppMessage.llm_processed == True
    ).update({"llm_processed": False})


def get_processed_messages_count(session):
    """Get count of processed messages."""
    return session.query(WhatsAppMessage).filter(
        WhatsAppMessage.llm_processed == True
    ).count()


def get_unprocessed_messages_count(session):
    """Get count of unprocessed messages."""
    return session.query(WhatsAppMessage).filter(
        WhatsAppMessage.llm_processed == False
    ).count()


def get_total_messages_count(session):
    """Get total number of messages."""
    return session.query(WhatsAppMessage).count()
