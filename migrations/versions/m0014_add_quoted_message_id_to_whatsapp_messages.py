"""add_quoted_message_id_to_whatsapp_messages

Add quoted_message_id field to whatsapp_messages table to support quoted messages.
This allows tracking which message is being quoted in a reply.

Revision ID: m0014
Revises: m0013
Create Date: 2025-01-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'm0014'
down_revision: Union[str, Sequence[str], None] = 'm0013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add quoted_message_id column to whatsapp_messages table."""
    # Add quoted_message_id column (nullable foreign key to whatsapp_messages.id)
    op.add_column('whatsapp_messages', sa.Column('quoted_message_id', sa.Integer(), nullable=True))
    op.create_foreign_key('whatsapp_messages_quoted_message_id_fkey', 'whatsapp_messages', 'whatsapp_messages', ['quoted_message_id'], ['id'])


def downgrade() -> None:
    """Remove the quoted_message_id column."""
    op.drop_constraint('whatsapp_messages_quoted_message_id_fkey', 'whatsapp_messages', type_='foreignkey')
    op.drop_column('whatsapp_messages', 'quoted_message_id')
