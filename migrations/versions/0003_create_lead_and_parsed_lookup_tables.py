"""create lead_categories and parsed_types"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
	op.create_table(
		"parsed_types",
		sa.Column("id", sa.Integer, primary_key=True),
		sa.Column("name", sa.Text, unique=True, nullable=False),
		sa.Column("description", sa.Text),
	)

	op.create_table(
		"lead_categories",
		sa.Column("id", sa.Integer, primary_key=True),
		sa.Column("name", sa.Text, unique=True, nullable=False),
		sa.Column("description", sa.Text),
		sa.Column("opening_message_template", sa.Text),
	)


def downgrade():
	op.drop_table("lead_categories")
	op.drop_table("parsed_types")
