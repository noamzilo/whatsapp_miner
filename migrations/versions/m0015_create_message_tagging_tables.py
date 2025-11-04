"""create_message_tagging_tables

Create taggers and message_tags tables for tracking human and model classifications.

Revision ID: m0015
Revises: m0014
Create Date: 2025-01-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'm0015'
down_revision: Union[str, Sequence[str], None] = 'm0014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    
    if not conn.dialect.has_table(conn, 'tagger_types'):
        op.create_table(
            'tagger_types',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.Text(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        op.execute("INSERT INTO tagger_types (id, name) VALUES (1, 'human'), (2, 'model')")
    
    if not conn.dialect.has_table(conn, 'taggers'):
        op.create_table(
            'taggers',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tagger_type_id', sa.Integer(), nullable=False),
            sa.Column('identifier', sa.Text(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['tagger_type_id'], ['tagger_types.id'], ),
            sa.UniqueConstraint('tagger_type_id', 'identifier', name='uq_tagger_type_identifier')
        )
    
    if not conn.dialect.has_table(conn, 'message_tags'):
        op.create_table(
            'message_tags',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('message_id', sa.Integer(), nullable=False),
            sa.Column('is_lead', sa.Boolean(), nullable=False),
            sa.Column('lead_category_id', sa.Integer(), nullable=True),
            sa.Column('tagger_id', sa.Integer(), nullable=False),
            sa.Column('tagged_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
            sa.Column('confidence_score', sa.Float(), nullable=False, server_default='1.0'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['message_id'], ['whatsapp_messages.id'], ),
            sa.ForeignKeyConstraint(['lead_category_id'], ['lead_categories.id'], ),
            sa.ForeignKeyConstraint(['tagger_id'], ['taggers.id'], ),
            sa.UniqueConstraint('message_id', 'tagger_id', 'tagged_at', name='uq_message_tagger_time')
        )
        
        op.create_index('ix_message_tags_message_id', 'message_tags', ['message_id'])
        op.create_index('ix_message_tags_tagger_id', 'message_tags', ['tagger_id'])
        op.create_index('ix_message_tags_tagged_at', 'message_tags', ['tagged_at'])
    
    result = conn.execute(sa.text("SELECT COUNT(*) FROM taggers WHERE tagger_type_id = 1 AND identifier = 'human_tagger'"))
    if result.scalar() == 0:
        op.execute("INSERT INTO taggers (tagger_type_id, identifier) VALUES (1, 'human_tagger')")


def downgrade() -> None:
    op.drop_index('ix_message_tags_tagged_at', 'message_tags')
    op.drop_index('ix_message_tags_tagger_id', 'message_tags')
    op.drop_index('ix_message_tags_message_id', 'message_tags')
    op.drop_table('message_tags')
    op.drop_table('taggers')
    op.drop_table('tagger_types')
