"""add_message_and_category_references_to_detected_leads

Add direct references to message and lead category in detected_leads table.
This allows easier querying and maintains audit trail through classification_id.

Revision ID: 0012
Revises: 69f389281cea
Create Date: 2025-08-04 09:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0012'
down_revision: Union[str, Sequence[str], None] = '69f389281cea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add message_id and lead_category_id columns to detected_leads table."""
    # Add message_id column (direct reference to original message)
    op.add_column('detected_leads', sa.Column('message_id', sa.Integer(), nullable=True))
    op.create_foreign_key('detected_leads_message_id_fkey', 'detected_leads', 'whatsapp_messages', ['message_id'], ['id'])
    
    # Add lead_category_id column (direct reference to lead category)
    op.add_column('detected_leads', sa.Column('lead_category_id', sa.Integer(), nullable=True))
    op.create_foreign_key('detected_leads_lead_category_id_fkey', 'detected_leads', 'lead_categories', ['lead_category_id'], ['id'])
    
    # Update existing records to populate the new columns
    # This will be done in the application code when processing leads


def downgrade() -> None:
    """Remove the added columns."""
    op.drop_constraint('detected_leads_lead_category_id_fkey', 'detected_leads', type_='foreignkey')
    op.drop_column('detected_leads', 'lead_category_id')
    
    op.drop_constraint('detected_leads_message_id_fkey', 'detected_leads', type_='foreignkey')
    op.drop_column('detected_leads', 'message_id') 