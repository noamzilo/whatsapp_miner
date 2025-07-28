"""Rename tables to clearer lead and classification naming"""

from alembic import op


revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade():
	# Rename tables
	op.rename_table('classifications', 'message_intent_classifications')
	op.rename_table('parsed_types', 'message_intent_types')
	op.rename_table('llm_prompt_templates', 'lead_classification_prompts')
	op.rename_table('leads', 'detected_leads')
	op.rename_table('business_leads', 'forwarded_leads')


def downgrade():
	op.rename_table('forwarded_leads', 'business_leads')
	op.rename_table('detected_leads', 'leads')
	op.rename_table('lead_classification_prompts', 'llm_prompt_templates')
	op.rename_table('message_intent_types', 'parsed_types')
	op.rename_table('message_intent_classifications', 'classifications')
