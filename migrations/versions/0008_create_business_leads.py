"""create business_leads"""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
	op.create_table(
		"business_leads",
		sa.Column("id", sa.Integer, primary_key=True),
		sa.Column("business_id", sa.Integer,
		          sa.ForeignKey("registered_businesses.id")),
		sa.Column("lead_id", sa.Integer,
		          sa.ForeignKey("leads.id")),
		sa.Column("status", sa.Text, nullable=False, server_default="new"),
		sa.Column("forwarded_at", sa.TIMESTAMP(timezone=True),
		          server_default=sa.func.now()),
		sa.Column("notes", sa.Text),
		# convenience index for billing queries
		sa.Index("ix_business_leads_business_id_forwarded_at",
		         "business_id", "forwarded_at"),
	)


def downgrade():
	op.drop_table("business_leads")
