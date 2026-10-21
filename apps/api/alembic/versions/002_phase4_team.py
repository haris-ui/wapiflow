"""Phase 4: Team & Multi-Agent schema additions.

Revision ID: 002_phase4_team
Revises: 001_initial_schema
Create Date: 2026-10-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_phase4_team'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. business_invitations
    op.create_table(
        'business_invitations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('business_id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=32), server_default='staff', nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('invited_by', sa.Uuid(), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by'], ['profiles.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
        sa.UniqueConstraint('business_id', 'email', name='uq_business_invitation_business_email'),
    )
    op.create_index('ix_business_invitations_business_id', 'business_invitations', ['business_id'])
    op.create_index('ix_business_invitations_email', 'business_invitations', ['email'])
    op.create_index('ix_business_invitations_token', 'business_invitations', ['token'])

    # 2. agent_activity_logs
    op.create_table(
        'agent_activity_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('business_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('resource_type', sa.String(length=64), nullable=True),
        sa.Column('resource_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['profiles.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agent_activity_logs_business_id', 'agent_activity_logs', ['business_id'])
    op.create_index('ix_agent_activity_logs_user_id', 'agent_activity_logs', ['user_id'])

    # 3. conversation_typing
    op.create_table(
        'conversation_typing',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('business_id', sa.Uuid(), nullable=False),
        sa.Column('conversation_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('is_typing', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('business_id', 'conversation_id', 'user_id', name='uq_conversation_typing'),
    )
    op.create_index('ix_conversation_typing_business_id', 'conversation_typing', ['business_id'])
    op.create_index('ix_conversation_typing_conversation_id', 'conversation_typing', ['conversation_id'])
    op.create_index('ix_conversation_typing_user_id', 'conversation_typing', ['user_id'])


def downgrade() -> None:
    op.drop_table('conversation_typing')
    op.drop_table('agent_activity_logs')
    op.drop_table('business_invitations')
