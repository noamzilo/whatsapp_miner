"""create leads"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
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
