"""create llm_prompt_templates"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
	op.create_table(
		"llm_prompt_templates",
		sa.Column("id", sa.Integer, primary_key=True),
		sa.Column("template_name", sa.Text, unique=True, nullable=False),
		sa.Column("prompt_text", sa.Text, nullable=False),
		sa.Column("version", sa.Text),
		sa.Column("created_at", sa.TIMESTAMP(timezone=True),
		          server_default=sa.func.now()),
	)


def downgrade():
	op.drop_table("llm_prompt_templates")
