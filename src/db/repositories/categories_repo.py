"""Repository for LeadCategory database operations."""

from src.db.models.lead_category import LeadCategory


def get_or_create_lead_category(session, category_name: str) -> int:
    """Get or create a lead category, returns category ID."""
    category = session.query(LeadCategory).filter_by(name=category_name).first()
    if not category:
        category = LeadCategory(
            name=category_name,
            description=f"Category for {category_name} leads",
            opening_message_template=f"Hi! I saw you're looking for {category_name} services. How can I help?"
        )
        session.add(category)
        session.flush()
    
    return category.id


def get_all_categories(session):
    """Get all categories."""
    return session.query(LeadCategory).all()


def get_category_by_name(session, category_name: str):
    """Get category by name."""
    return session.query(LeadCategory).filter_by(name=category_name).first()


def get_category_names(session):
    """Get all category names."""
    categories = session.query(LeadCategory.name).all()
    return [cat[0] for cat in categories]


def delete_all_categories(session):
    """Delete all categories."""
    return session.query(LeadCategory).delete()


def get_all_categories_count(session):
    """Get total number of categories."""
    return session.query(LeadCategory).count()


def get_categories_count(session):
    """Get count of categories."""
    return session.query(LeadCategory).count()
