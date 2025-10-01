"""Add is_real column to whatsapp_messages table"""

from alembic import op
import sqlalchemy as sa

revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_real column with default value True (existing messages are real)
    op.add_column('whatsapp_messages', 
                  sa.Column('is_real', sa.Boolean(), nullable=False, server_default='true'))


def downgrade():
    # Remove is_real column
    op.drop_column('whatsapp_messages', 'is_real') 