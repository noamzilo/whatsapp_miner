"""create messages"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
	op.create_table(
		"messages",
		sa.Column("id", sa.Integer, primary_key=True),
		sa.Column("message_id", sa.Text, unique=True, nullable=False),
		sa.Column("sender_id", sa.Integer,
		          sa.ForeignKey("whatsapp_users.id")),
		sa.Column("group_id", sa.Integer,
		          sa.ForeignKey("whatsapp_groups.id")),
		sa.Column("timestamp", sa.TIMESTAMP(timezone=True), nullable=False),
		sa.Column("raw_text", sa.Text, nullable=False),
		sa.Column("message_type", sa.Text),
		sa.Column("is_forwarded", sa.Boolean),
		sa.Column("llm_processed", sa.Boolean,
		          server_default="false", nullable=False),
	)


def downgrade():
	op.drop_table("messages")
