"""remove_confidence_score_from_classifications

Revision ID: 69f389281cea
Revises: 0011
Create Date: 2025-08-01 12:05:44.319380

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69f389281cea'
down_revision: Union[str, Sequence[str], None] = '0011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remove confidence_score column from message_intent_classifications table
    op.drop_column('message_intent_classifications', 'confidence_score')


def downgrade() -> None:
    """Downgrade schema."""
    # Add back confidence_score column to message_intent_classifications table
    op.add_column('message_intent_classifications', 
                  sa.Column('confidence_score', sa.Float, nullable=True))
