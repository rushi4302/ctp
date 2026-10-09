"""add_civic_issues_and_moderation

Revision ID: 5e9f1a2b3c4d
Revises: 4d8e9f2a1b3c
Create Date: 2026-09-25 23:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e9f1a2b3c4d'
down_revision: Union[str, Sequence[str], None] = '4d8e9f2a1b3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Add FIELD_WORKER to Postgres userrole enum if postgres
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'FIELD_WORKER'")

    # 2. Create civic_issues table
    op.create_table(
        'civic_issues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('severity', sa.String(length=50), server_default='MEDIUM', nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column('locality', sa.String(length=100), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('ward', sa.String(length=100), nullable=True),
        sa.Column('report_count', sa.Integer(), server_default='1', nullable=False),
        sa.Column('assigned_department_id', sa.String(length=100), nullable=True),
        sa.Column('assigned_worker_id', sa.Integer(), nullable=True),
        sa.Column('ai_category', sa.String(length=100), nullable=True),
        sa.Column('ai_confidence', sa.Float(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('resolution_evidence_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_worker_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_civic_issues_id'), 'civic_issues', ['id'], unique=False)
    op.create_index(op.f('ix_civic_issues_category'), 'civic_issues', ['category'], unique=False)
    op.create_index(op.f('ix_civic_issues_status'), 'civic_issues', ['status'], unique=False)
    op.create_index(op.f('ix_civic_issues_severity'), 'civic_issues', ['severity'], unique=False)
    op.create_index(op.f('ix_civic_issues_ward'), 'civic_issues', ['ward'], unique=False)

    # 3. Create civic_issue_status_logs table
    op.create_table(
        'civic_issue_status_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('civic_issue_id', sa.Integer(), nullable=False),
        sa.Column('changed_by_id', sa.Integer(), nullable=True),
        sa.Column('previous_status', sa.String(length=50), nullable=False),
        sa.Column('new_status', sa.String(length=50), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['changed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['civic_issue_id'], ['civic_issues.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_civic_issue_status_logs_id'), 'civic_issue_status_logs', ['id'], unique=False)
    op.create_index(op.f('ix_civic_issue_status_logs_civic_issue_id'), 'civic_issue_status_logs', ['civic_issue_id'], unique=False)

    # 4. Add columns to reports
    op.add_column('reports', sa.Column('civic_issue_id', sa.Integer(), nullable=True))
    op.add_column('reports', sa.Column('moderation_status', sa.String(length=50), server_default='ACTIVE', nullable=False))
    op.add_column('reports', sa.Column('rejected_at', sa.DateTime(), nullable=True))
    op.add_column('reports', sa.Column('rejected_by_id', sa.Integer(), nullable=True))
    op.add_column('reports', sa.Column('rejection_reason', sa.Text(), nullable=True))

    op.create_foreign_key('fk_reports_civic_issue_id', 'reports', 'civic_issues', ['civic_issue_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_reports_rejected_by_id', 'reports', 'users', ['rejected_by_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_reports_civic_issue_id'), 'reports', ['civic_issue_id'], unique=False)
    op.create_index(op.f('ix_reports_moderation_status'), 'reports', ['moderation_status'], unique=False)

    # 5. Backfill existing reports into civic_issues
    # For each existing report, create a civic_issue and associate it
    op.execute("""
        INSERT INTO civic_issues (
            title, description, category, status, severity,
            latitude, longitude, address, locality, city, district, state, postal_code, ward,
            report_count, ai_category, ai_confidence, created_at, updated_at
        )
        SELECT
            r.title, r.description, r.category,
            CASE
                WHEN r.status = 'RESOLVED' THEN 'RESOLVED'
                WHEN r.status = 'IN_PROGRESS' THEN 'IN_PROGRESS'
                WHEN r.status = 'VERIFIED' THEN 'ASSIGNED'
                ELSE 'PENDING'
            END,
            r.severity,
            r.latitude, r.longitude, r.address, r.locality, r.city, r.district, r.state, r.postal_code, r.ward,
            1, r.ai_category, r.ai_confidence, r.created_at, r.updated_at
        FROM reports r
        WHERE r.civic_issue_id IS NULL;
    """)

    # Link reports back to the created civic_issues by matching coordinates and creation time
    op.execute("""
        UPDATE reports r
        SET civic_issue_id = ci.id
        FROM civic_issues ci
        WHERE r.civic_issue_id IS NULL
          AND r.title = ci.title
          AND r.latitude = ci.latitude
          AND r.longitude = ci.longitude
          AND r.created_at = ci.created_at;
    """)


def downgrade() -> None:
    op.drop_index(op.f('ix_reports_moderation_status'), table_name='reports')
    op.drop_index(op.f('ix_reports_civic_issue_id'), table_name='reports')
    op.drop_constraint('fk_reports_rejected_by_id', 'reports', type_='foreignkey')
    op.drop_constraint('fk_reports_civic_issue_id', 'reports', type_='foreignkey')
    op.drop_column('reports', 'rejection_reason')
    op.drop_column('reports', 'rejected_by_id')
    op.drop_column('reports', 'rejected_at')
    op.drop_column('reports', 'moderation_status')
    op.drop_column('reports', 'civic_issue_id')

    op.drop_index(op.f('ix_civic_issue_status_logs_civic_issue_id'), table_name='civic_issue_status_logs')
    op.drop_index(op.f('ix_civic_issue_status_logs_id'), table_name='civic_issue_status_logs')
    op.drop_table('civic_issue_status_logs')

    op.drop_index(op.f('ix_civic_issues_ward'), table_name='civic_issues')
    op.drop_index(op.f('ix_civic_issues_severity'), table_name='civic_issues')
    op.drop_index(op.f('ix_civic_issues_status'), table_name='civic_issues')
    op.drop_index(op.f('ix_civic_issues_category'), table_name='civic_issues')
    op.drop_index(op.f('ix_civic_issues_id'), table_name='civic_issues')
    op.drop_table('civic_issues')
