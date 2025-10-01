"""Rename messages table to whatsapp_messages"""

from alembic import op

revision = 'm0010'
down_revision = 'm0009'
branch_labels = None
depends_on = None


def upgrade():
	op.rename_table('messages', 'whatsapp_messages')


def downgrade():
	op.rename_table('whatsapp_messages', 'messages')
