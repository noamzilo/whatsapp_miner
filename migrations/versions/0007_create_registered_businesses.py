"""create registered_businesses"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
	op.create_table(
		"registered_businesses",
		sa.Column("id", sa.Integer, primary_key=True),
		sa.Column("business_name", sa.Text, nullable=False),
		sa.Column("contact_name", sa.Text),
		sa.Column("contact_phone", sa.Text),
		sa.Column("contact_email", sa.Text),
		sa.Column("lead_category_id", sa.Integer,
		          sa.ForeignKey("lead_categories.id")),
		sa.Column("service_area_city", sa.Text),
		sa.Column("service_area_neighbourhood", sa.Text),
		sa.Column("notes", sa.Text),
		sa.Column("created_at", sa.TIMESTAMP(timezone=True),
		          server_default=sa.func.now()),
	)


def downgrade():
	op.drop_table("registered_businesses")
