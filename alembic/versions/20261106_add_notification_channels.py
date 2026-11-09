"""add notification channels and delivery metadata

Revision ID: 20261106_01
Revises: 
Create Date: 2026-11-06 13:25:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '20261106_01'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('notifications', sa.Column('channel', sa.String(length=20), server_default='in_app', nullable=False))
    op.add_column('notifications', sa.Column('delivery_status', sa.String(length=20), server_default='delivered', nullable=False))
    op.add_column('notifications', sa.Column('scheduled_send_time', sa.DateTime(), nullable=True))
    op.add_column('notifications', sa.Column('action_url', sa.String(length=500), nullable=True))
    op.add_column('notifications', sa.Column('template_id', sa.String(length=50), nullable=True))
    op.add_column('notifications', sa.Column('language', sa.String(length=10), server_default='vi', nullable=False))

def downgrade() -> None:
    op.drop_column('notifications', 'language')
    op.drop_column('notifications', 'template_id')
    op.drop_column('notifications', 'action_url')
    op.drop_column('notifications', 'scheduled_send_time')
    op.drop_column('notifications', 'delivery_status')
    op.drop_column('notifications', 'channel')

