"""add_location_and_timestamp_metadata

Revision ID: 4d8e9f2a1b3c
Revises: ede26fe506da
Create Date: 2026-09-25 19:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d8e9f2a1b3c'
down_revision: Union[str, Sequence[str], None] = 'ede26fe506da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('reports', sa.Column('location_accuracy', sa.Float(), nullable=True))
    op.add_column('reports', sa.Column('capture_timestamp', sa.DateTime(), nullable=True))
    op.add_column('reports', sa.Column('locality', sa.String(length=100), nullable=True))
    op.add_column('reports', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('reports', sa.Column('district', sa.String(length=100), nullable=True))
    op.add_column('reports', sa.Column('state', sa.String(length=100), nullable=True))
    op.add_column('reports', sa.Column('postal_code', sa.String(length=20), nullable=True))
    op.add_column('report_media', sa.Column('capture_timestamp', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('report_media', 'capture_timestamp')
    op.drop_column('reports', 'postal_code')
    op.drop_column('reports', 'state')
    op.drop_column('reports', 'district')
    op.drop_column('reports', 'city')
    op.drop_column('reports', 'locality')
    op.drop_column('reports', 'capture_timestamp')
    op.drop_column('reports', 'location_accuracy')
