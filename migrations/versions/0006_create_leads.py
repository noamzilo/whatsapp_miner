"""create leads

This table is ONLY for actual business leads detected in messages.
Non-lead messages should NOT be stored in this table.
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
	# This table stores ONLY actual business leads detected in WhatsApp messages
	# Non-lead messages should NOT be stored here - they should just be marked as processed
	op.create_table(
		"leads",
		sa.Column("id", sa.Integer, primary_key=True),
		sa.Column("classification_id", sa.Integer,
		          sa.ForeignKey("classifications.id")),
		sa.Column("user_id", sa.Integer,
		          sa.ForeignKey("whatsapp_users.id")),
		sa.Column("group_id", sa.Integer,
		          sa.ForeignKey("whatsapp_groups.id")),
		sa.Column("lead_for", sa.Text),
		sa.Column("created_at", sa.TIMESTAMP(timezone=True),
		          server_default=sa.func.now()),
	)


def downgrade():
	op.drop_table("leads")
