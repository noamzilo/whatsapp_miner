"""create whatsapp_users and whatsapp_groups"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
	op.create_table(
		"whatsapp_users",
		sa.Column("id", sa.Integer, primary_key=True),
		sa.Column("whatsapp_id", sa.Text, unique=True, nullable=False),
		sa.Column("display_name", sa.Text),
		sa.Column("created_at", sa.TIMESTAMP(timezone=True),
		          server_default=sa.func.now()),
	)

	op.create_table(
		"whatsapp_groups",
		sa.Column("id", sa.Integer, primary_key=True),
		sa.Column("whatsapp_group_id", sa.Text, unique=True, nullable=False),
		sa.Column("group_name", sa.Text),
		sa.Column("location_city", sa.Text),
		sa.Column("location_neighbourhood", sa.Text),
		sa.Column("location", sa.Text),
		sa.Column("created_at", sa.TIMESTAMP(timezone=True),
		          server_default=sa.func.now()),
	)


def downgrade():
	op.drop_table("whatsapp_groups")
	op.drop_table("whatsapp_users")