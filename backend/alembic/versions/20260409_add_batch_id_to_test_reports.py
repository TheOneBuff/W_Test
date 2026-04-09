"""Add batch_id column to test_reports table

Revision ID: 20260409
Revises: 
Create Date: 2026-04-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260409'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 batch_id 字段到 test_reports 表
    op.add_column('test_reports', sa.Column('batch_id', sa.String(length=50), nullable=True))
    # 添加索引
    op.create_index('idx_batch_id', 'test_reports', ['batch_id'])


def downgrade() -> None:
    # 移除索引
    op.drop_index('idx_batch_id', table_name='test_reports')
    # 移除 batch_id 字段
    op.drop_column('test_reports', 'batch_id')
