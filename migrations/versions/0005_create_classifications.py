"""create classifications"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
	op.create_table(
		"classifications",
		sa.Column("id", sa.Integer, primary_key=True),
		sa.Column("message_id", sa.Integer,
		          sa.ForeignKey("messages.id")),
		sa.Column("prompt_template_id", sa.Integer,
		          sa.ForeignKey("llm_prompt_templates.id")),
		sa.Column("parsed_type_id", sa.Integer,
		          sa.ForeignKey("parsed_types.id")),
		sa.Column("lead_category_id", sa.Integer,
		          sa.ForeignKey("lead_categories.id")),
		sa.Column("confidence_score", sa.Float),
		sa.Column("raw_llm_output", sa.JSON),
		sa.Column("classified_at", sa.TIMESTAMP(timezone=True),
		          server_default=sa.func.now()),
	)


def downgrade():
	op.drop_table("classifications")
